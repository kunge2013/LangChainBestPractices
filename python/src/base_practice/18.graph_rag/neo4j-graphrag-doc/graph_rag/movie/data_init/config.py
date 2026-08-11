# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
Neo4j 数据库连接配置
"""
import os
from dotenv import load_dotenv

# [AGC:START] tool=Cc author=fangkun
# 加载环境变量
load_dotenv()

# Neo4j 连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
# [AGC:END]
