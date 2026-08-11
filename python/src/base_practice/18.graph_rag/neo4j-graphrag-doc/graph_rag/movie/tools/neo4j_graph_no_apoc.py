# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
自定义 Neo4j Graph 类
不依赖 APOC 插件，使用纯 Cypher 获取 schema
"""
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase
from config import settings


# [AGC:START] tool=Cc author=fangkun


class SimpleNeo4jGraph:
    """
    简化的 Neo4j Graph 类
    不依赖 APOC，使用纯 Cypher 查询获取 schema
    """

    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self._url = url or settings.neo4j.uri
        self._username = username or settings.neo4j.username
        self._password = password or settings.neo4j.password
        self._database = database or settings.neo4j.database

        self._driver = GraphDatabase.driver(
            self._url,
            auth=(self._username, self._password)
        )

        # 预定义的 schema（电影领域）
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

    def query(
        self,
        cypher_query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """执行 Cypher 查询"""
        with self._driver.session(database=self._database) as session:
            result = session.run(cypher_query, params or {})
            return [record.data() for record in result]

    @property
    def structured_schema(self) -> Dict[str, Any]:
        """返回结构化 schema"""
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

    def close(self):
        """关闭连接"""
        self._driver.close()


# [AGC:END]
