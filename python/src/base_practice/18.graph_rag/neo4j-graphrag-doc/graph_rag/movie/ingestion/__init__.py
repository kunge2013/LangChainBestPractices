# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
图数据导入模块
提供将电影、人物、制片厂数据导入 Neo4j 的功能
"""
from .ingest_graph import ingest_movies_data

__all__ = ["ingest_movies_data"]
