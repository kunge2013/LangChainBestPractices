# [AGC:FILE] tool=Cc author=fangkun date=2026-08-12
import os
from contextlib import contextmanager

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(override=True)

_driver = None


# [AGC:START] tool=Cc author=fangkun
def _get_driver():
    """懒加载并返回 Neo4j driver 单例。"""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "")
        username = os.getenv("NEO4J_USERNAME", "")
        password = os.getenv("NEO4J_PASSWORD", "")
        _driver = GraphDatabase.driver(uri, auth=(username, password))
    return _driver
# [AGC:END]


# [AGC:START] tool=Cc author=fangkun
@contextmanager
def get_session():
    """获取 Neo4j session 的上下文管理器。"""
    driver = _get_driver()
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    with driver.session(database=database) as session:
        yield session
# [AGC:END]


# [AGC:START] tool=Cc author=fangkun
def close_driver():
    """关闭 driver 并重置单例。"""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
# [AGC:END]
