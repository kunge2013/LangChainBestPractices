# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
数据初始化模块
提供 Neo4j 数据操作的工具函数和连接管理
"""
from .config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    NEO4J_DATABASE
)
from .neo4j_utils import (
    Neo4jConnection,
    print_results,
    clear_database
)

__all__ = [
    'NEO4J_URI',
    'NEO4J_USERNAME',
    'NEO4J_PASSWORD',
    'NEO4J_DATABASE',
    'Neo4jConnection',
    'print_results',
    'clear_database'
]
