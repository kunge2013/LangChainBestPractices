# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
结构化查询工具
使用 GraphCypherQAChain 自动生成 Cypher 查询，实现对电影、演员、评分等的精确查询
"""
from langchain_core.tools import Tool
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.language_models import BaseLLM
from config import settings


# [AGC:START] tool=Cc author=fangkun


def create_graph_query_tool(llm: BaseLLM) -> Tool:
    """创建结构化查询工具"""

    # 初始化 Neo4j Graph（传入配置参数）
    graph = Neo4jGraph(
        url=settings.neo4j.uri,
        username=settings.neo4j.username,
        password=settings.neo4j.password,
        database=settings.neo4j.database,
    )

    # 创建 Cypher QA Chain
    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        return_intermediate_steps=False
    )

    def query_func(question: str) -> str:
        """执行图查询"""
        try:
            result = chain.run(question)
            return result
        except Exception as e:
            return f"查询失败: {str(e)}"

    return Tool(
        name="graph_query",
        description="用于结构化查询电影信息、演员信息、评分等精确问题。例如：'谁演了 Inception'、'这部电影评分多少'",
        func=query_func
    )


# [AGC:END]
