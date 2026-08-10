# [AGC:FILE] tool=Cc author=fangkun date=2026-08-10
# [AGC:START] tool=Cc author=fangkun
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Union

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from neo4j import GraphDatabase
# from neo4j_graphrag.embeddings import OpenAIEmbeddings
# from langchain_huggingface import HuggingFaceEmbeddings
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
from neo4j_graphrag.experimental.components.data_loader import DataLoader
from neo4j_graphrag.experimental.components.text_splitters.langchain import LangChainTextSplitterAdapter
from neo4j_graphrag.experimental.components.types import LoadedDocument, DocumentInfo
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm.openai_llm import OpenAILLM


class QwenLLM(OpenAILLM):
    """
    自定义 LLM 类，禁用 structured output。
    Qwen 模型对 json_schema 格式支持不完善，需要使用更宽松的 V1 模式。
    """
    supports_structured_output: bool = False

from rag_schema_from_onto import getSchemaFromOnto

# 开启 neo4j_graphrag 日志，方便追踪 pipeline 各步骤进度
logging.basicConfig(level=logging.INFO)
logging.getLogger("neo4j_graphrag").setLevel(logging.DEBUG)

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


# Create DocumentLoader
class PdfLoaderWithPageBreaks(DataLoader):
    async def run(self, filepath: Union[str, Path], metadata: Optional[Dict[str, str]] = None) -> LoadedDocument:
        loader = PyPDFLoader(filepath)
        text = ''
        async for page in loader.alazy_load():
            text = text + " __PAGE__BREAK__ " + page.page_content
        return LoadedDocument(
            text=text,
            document_info=DocumentInfo(path=filepath), )


async def main():
    # Connect to the Neo4j database
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    # 使用相对于当前文件的路径
    ontos_path = Path(__file__).parent.parent / "ontos" / "customer.ttl"
    neo4j_schema = await getSchemaFromOnto(str(ontos_path))
    print(neo4j_schema)

    # Create a Splitter object
    splitter = LangChainTextSplitterAdapter(
        CharacterTextSplitter(chunk_size=15_000, chunk_overlap=0, separator=" __PAGE__BREAK__ ")
    )

    # Create an Embedder object
    # embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    embedder = SentenceTransformerEmbeddings(model="all-MiniLM-L6-v2")
    # embedder = SentenceTransformerEmbeddings(model="text2vec-base-chinese")

    # Instantiate the LLM (使用 DashScope/Qwen OpenAI 兼容接口)
    llm = QwenLLM(
        model_name=os.environ.get("OPENAI_MODEL", "qwen-plus"),
        model_params={
            "temperature": float(os.environ.get("OPENAI_TEMPERATURE", "0")),
        },
        base_url=os.environ.get("OPENAI_BASE_URL"),
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    # instantiate the SimpleKGPipeline
    kg_builder = SimpleKGPipeline(
        llm=llm,
        driver=driver,
        file_loader=PdfLoaderWithPageBreaks(),
        text_splitter=splitter,
        embedder=embedder,
        schema=neo4j_schema,
        on_error="IGNORE",
        from_file=True,
        neo4j_database="neo4j",
    )

    # 使用相对于当前文件的路径
    data_path = Path(__file__).parent / "data" / "credit-notes.pdf"
    print(f"开始处理 PDF: {data_path}")

    # load credit notes，加超时保护
    try:
        result = await asyncio.wait_for(
            kg_builder.run_async(file_path=str(data_path)),
            timeout=6000  # 总超时 100 分钟
        )
        print(f"Pipeline 完成: {result}")

        # 查询实际创建的向量索引名称
        index_query = """
        SHOW INDEXES
        WHERE type = 'VECTOR' AND entityType = 'NODE'
        RETURN name
        """
        index_result = driver.execute_query(index_query)
        if index_result.records:
            actual_index_name = index_result.records[0]["name"]
            print(f"\n=== 向量索引信息 ===")
            print(f"实际创建的索引名称: {actual_index_name}")
            print(f"请在查询代码中使用此索引名: INDEX_NAME = '{actual_index_name}'")
            print(f"===================\n")
    except asyncio.TimeoutError:
        print("Pipeline 执行超时（10分钟），已中断")
        raise

    # perform entity resolution
    print("Performing Additional Entity Resolution")
    result = driver.execute_query('''
    MATCH (n:Article)
    WITH n.articleId AS id, collect(n) as nodes
    CALL apoc.refactor.mergeNodes(nodes, {
      properties: {
          `.*`: 'combine'
      },
      mergeRels: true
    })
    YIELD node
    RETURN node;
    ''')

    print(f"result ={result}")
    result= driver.execute_query('''
    MATCH (n:Order)
    WITH n.orderId AS id, collect(n) as nodes
    CALL apoc.refactor.mergeNodes(nodes, {
      properties: {
          `.*`: 'combine'
      },
      mergeRels: true
    })
    YIELD node
    RETURN node
    ''')

    print(f"result ={result}")
    # print("Removing Unneeded Nodes")
    # driver.execute_query('MATCH (n:Product) WHERE n:__Entity__ DETACH DELETE n')

    driver.close()


if __name__ == "__main__":
    asyncio.run(main())
# [AGC:END]
