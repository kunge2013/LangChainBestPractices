# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
Neo4j 连接工具模块
提供数据库连接管理和 Cypher 执行工具函数
"""
from neo4j import Neo4jDriver
from neo4j import GraphDatabase
from typing import Optional, List, Dict, Any
from data_init.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

# [AGC:START] tool=Cc author=fangkun


class Neo4jConnection:
    """Neo4j 数据库连接管理类"""

    _instance: Optional[Neo4jDriver] = None

    @classmethod
    def get_driver(cls) -> Neo4jDriver:
        """获取 Neo4j 驱动实例（单例模式）"""
        if cls._instance is None:
            cls._instance = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
            )
        return cls._instance

    @classmethod
    def close(cls) -> None:
        """关闭数据库连接"""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None

    @classmethod
    def execute_query(
        cls,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        执行 Cypher 查询并返回结果

        Args:
            query: Cypher 查询语句
            parameters: 查询参数
            database: 数据库名称

        Returns:
            查询结果列表
        """
        driver = cls.get_driver()
        db = database or NEO4J_DATABASE
        results = []

        with driver.session(database=db) as session:
            result = session.run(query, parameters)
            for record in result:
                results.append(dict(record))

        return results

    @classmethod
    def execute_write(
        cls,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        执行写入操作（创建、更新、删除）

        Args:
            query: Cypher 写入语句
            parameters: 查询参数
            database: 数据库名称

        Returns:
            操作结果列表
        """
        driver = cls.get_driver()
        db = database or NEO4J_DATABASE
        results = []

        def _execute(tx):
            result = tx.run(query, parameters)
            for record in result:
                results.append(dict(record))
            return results

        with driver.session(database=db) as session:
            session.execute_write(_execute)

        return results


def print_results(title: str, results: List[Dict[str, Any]]) -> None:
    """
    格式化打印查询结果

    Args:
        title: 结果标题
        results: 查询结果列表
    """
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

    if not results:
        print("  (无结果)")
        return

    for i, record in enumerate(results, 1):
        print(f"\n  [{i}]")
        for key, value in record.items():
            print(f"      {key}: {value}")


def clear_database() -> None:
    """清空数据库中的所有数据"""
    query = "MATCH (n) DETACH DELETE n"
    Neo4jConnection.execute_write(query)
    print("\n[INFO] 数据库已清空")
# [AGC:END]
