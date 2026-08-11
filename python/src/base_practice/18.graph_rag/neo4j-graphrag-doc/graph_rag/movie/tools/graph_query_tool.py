# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
结构化查询工具
使用 GraphCypherQAChain 自动生成 Cypher 查询，实现对电影、演员、评分等的精确查询
不依赖 APOC 插件
"""
from langchain_core.tools import Tool
from langchain_neo4j import GraphCypherQAChain
from langchain_core.language_models import BaseLLM
from neo4j import GraphDatabase
from config import settings


# [AGC:START] tool=Cc author=fangkun


class SimpleNeo4jGraph:
    """
    简化的 Neo4j Graph 类
    不依赖 APOC，提供 GraphCypherQAChain 所需的最小接口
    """

    def __init__(self):
        self._driver = GraphDatabase.driver(
            settings.neo4j.uri,
            auth=(settings.neo4j.username, settings.neo4j.password)
        )
        self._database = settings.neo4j.database

        # 预定义 schema（电影领域）
        self.schema = """
        Node properties:
        Movie {title: STRING, released: INTEGER, rating: FLOAT, tagline: STRING, plot_summary: STRING, genres: LIST}
        Person {name: STRING, born: INTEGER, gender: STRING}
        Studio {name: STRING, country: STRING}

        Relationship properties:
        ACTED_IN {roles: LIST}
        DISTRIBUTED_BY {year: INTEGER}

        Relationships:
        (:Person)-[:ACTED_IN]->(:Movie)
        (:Person)-[:DIRECTED]->(:Movie)
        (:Person)-[:WROTE]->(:Movie)
        (:Studio)-[:DISTRIBUTED_BY]->(:Movie)
        """

    def query(self, cypher_query: str, params: dict = None) -> list:
        """执行 Cypher 查询"""
        with self._driver.session(database=self._database) as session:
            result = session.run(cypher_query, params or {})
            return [record.data() for record in result]

    def close(self):
        """关闭连接"""
        self._driver.close()


def create_graph_query_tool(llm: BaseLLM) -> Tool:
    """创建结构化查询工具"""

    # 初始化简化的 Neo4j Graph（不依赖 APOC）
    graph = SimpleNeo4jGraph()

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
