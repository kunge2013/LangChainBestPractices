from neo4j import GraphDatabase
from neo4j_graphrag.retrievers import VectorRetriever
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings

import os
from dotenv import load_dotenv
import logging


class QwenLLM(OpenAILLM):
    """
    自定义 LLM 类，禁用 structured output。
    Qwen 模型对 json_schema 格式支持不完善，需要使用更宽松的 V1 模式。
    """
    supports_structured_output: bool = False


# 开启 neo4j_graphrag 日志，方便追踪 pipeline 各步骤进度
logging.basicConfig(level=logging.INFO)
logging.getLogger("neo4j_graphrag").setLevel(logging.DEBUG)

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# 1. Neo4j driver
URI = NEO4J_URI
AUTH = (NEO4J_USERNAME, NEO4J_PASSWORD)

# Connect to Neo4j database
driver = GraphDatabase.driver(URI, auth=AUTH)

# 2. Retriever
# Create Embedder object, needed to convert the user question (text) to a vector
embedder = SentenceTransformerEmbeddings(model="all-MiniLM-L6-v2")

# 自动发现向量索引
index_query = """
SHOW INDEXES
WHERE type = 'VECTOR' AND entityType = 'NODE'
RETURN name
"""
with driver.session() as session:
    result = session.run(index_query)
    records = result.fetch_all()
    if not records:
        raise Exception(
            "No vector index found in Neo4j. "
            "Run unstructured_ingest.py first to create the index."
        )
    INDEX_NAME = records[0]["name"]
    print(f"Using vector index: {INDEX_NAME}")

# Initialize the retriever
retriever = VectorRetriever(driver, INDEX_NAME, embedder)

# 3. LLM
# Note: the OPENAI_API_KEY must be in the env vars
llm = QwenLLM(
    model_name=os.environ.get("OPENAI_MODEL", "qwen-plus"),
    model_params={
        "temperature": float(os.environ.get("OPENAI_TEMPERATURE", "0")),
    },
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Initialize the RAG pipeline
rag = GraphRAG(retriever=retriever, llm=llm)

# Query the graph
query_text = "How do I do similarity search in Neo4j?"
response = rag.search(query_text=query_text, retriever_config={"top_k": 5})
print(response.answer)
