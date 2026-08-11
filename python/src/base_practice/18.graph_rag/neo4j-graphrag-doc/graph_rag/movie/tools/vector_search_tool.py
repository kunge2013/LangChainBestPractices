# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
语义搜索工具
使用 Neo4jVector 基于 plot_summary 做相似度搜索
Embedding 使用 HuggingFace 本地模型
"""
from langchain_core.tools import Tool
from langchain_neo4j import Neo4jVector
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.language_models import BaseLLM
from config import settings


# [AGC:START] tool=Cc author=fangkun


def create_vector_search_tool(llm: BaseLLM) -> Tool:
    """创建语义搜索工具"""

    # 初始化 HuggingFace Embedding（本地模型）
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding.model_name,
        model_kwargs={"device": settings.embedding.device},
        encode_kwargs={"normalize_embeddings": True},
        cache_folder=settings.embedding.cache_dir,
    )

    # 初始化 Neo4j Vector Store（传入连接参数）
    vector_store = Neo4jVector.from_existing_index(
        embedding=embeddings,
        url=settings.neo4j.uri,
        username=settings.neo4j.username,
        password=settings.neo4j.password,
        database=settings.neo4j.database,
        index_name="movie_plot_summary_index",
        text_node_property="plot_summary",
        embedding_node_property="plot_summary_embedding",
    )

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    def search_func(query: str) -> str:
        """执行语义搜索"""
        try:
            docs = retriever.invoke(query)
            if not docs:
                return "未找到相关电影"

            results = []
            for i, doc in enumerate(docs, 1):
                results.append(f"{i}. {doc.page_content}")

            return "\n".join(results)
        except Exception as e:
            return f"搜索失败: {str(e)}"

    return Tool(
        name="vector_search",
        description="用于语义搜索，基于剧情简介的相似度匹配。例如：'类似 XX 的电影'、'关于太空的电影'",
        func=search_func
    )


# [AGC:END]
