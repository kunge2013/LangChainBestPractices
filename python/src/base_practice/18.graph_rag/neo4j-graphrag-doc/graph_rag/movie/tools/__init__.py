# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
结构化查询工具模块
提供基于 GraphCypherQAChain 的图查询工具
"""
from .graph_query_tool import create_graph_query_tool

# [AGC:START] tool=Cc author=fangkun

__all__ = ["create_graph_query_tool"]

# [AGC:END]
