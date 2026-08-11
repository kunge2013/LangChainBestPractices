# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
结构化查询工具
使用 GraphCypherQAChain 自动生成 Cypher 查询，实现对电影、演员、评分等的精确查询
不依赖 APOC 插件
"""
from langchain_core.tools import Tool
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.language_models import BaseLLM
from neo4j import GraphDatabase
from config import settings


# [AGC:START] tool=Cc author=fangkun


class NoAPOCNeo4jGraph(Neo4jGraph):
    """
    Neo4jGraph 的子类，不依赖 APOC 插件
    覆盖 refresh_schema 方法，使用预定义的 schema
    """

    def __init__(self, *args, **kwargs):
        # 调用父类初始化，但捕获可能的 APOC 错误
        try:
            super().__init__(*args, **kwargs)
        except Exception as e:
            if "apoc" in str(e).lower():
                # 如果是因为 APOC，跳过 schema 刷新
                print(f"[WARN] APOC not available, using predefined schema: {e}")
                # 手动初始化必要的属性
                self._driver = GraphDatabase.driver(
                    kwargs.get('url', settings.neo4j.uri),
                    auth=(
                        kwargs.get('username', settings.neo4j.username),
                        kwargs.get('password', settings.neo4j.password)
                    )
                )
                self._database = kwargs.get('database', settings.neo4j.database)
                self.structured_schema = self._get_predefined_schema()
                self.schema = self._format_schema()
            else:
                raise

    def _get_predefined_schema(self):
        """返回预定义的结构化 schema"""
        return {
            "node_props": {
                "Movie": [
                    {"property": "title", "type": "STRING"},
                    {"property": "released", "type": "INTEGER"},
                    {"property": "rating", "type": "FLOAT"},
                    {"property": "tagline", "type": "STRING"},
                    {"property": "plot_summary", "type": "STRING"},
                    {"property": "genres", "type": "LIST"},
                ],
                "Person": [
                    {"property": "name", "type": "STRING"},
                    {"property": "born", "type": "INTEGER"},
                    {"property": "gender", "type": "STRING"},
                ],
                "Studio": [
                    {"property": "name", "type": "STRING"},
                    {"property": "country", "type": "STRING"},
                ],
            },
            "rel_props": {
                "ACTED_IN": [{"property": "roles", "type": "LIST"}],
                "DISTRIBUTED_BY": [{"property": "year", "type": "INTEGER"}],
            },
            "relationships": [
                {"start": "Person", "type": "ACTED_IN", "end": "Movie"},
                {"start": "Person", "type": "DIRECTED", "end": "Movie"},
                {"start": "Person", "type": "WROTE", "end": "Movie"},
                {"start": "Studio", "type": "DISTRIBUTED_BY", "end": "Movie"},
            ],
        }

    def _format_schema(self):
        """格式化 schema 为字符串"""
        return """
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

    def refresh_schema(self):
        """覆盖 refresh_schema，不依赖 APOC"""
        self.structured_schema = self._get_predefined_schema()
        self.schema = self._format_schema()


def create_graph_query_tool(llm: BaseLLM) -> Tool:
    """创建结构化查询工具"""

    # 初始化 Neo4j Graph（不依赖 APOC）
    graph = NoAPOCNeo4jGraph(
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
        return_intermediate_steps=False,
        allow_dangerous_requests=True,  # 确认允许生成 Cypher 查询
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
