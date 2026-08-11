# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
from pydantic import BaseModel
from typing import Optional


# [AGC:START] tool=Cc author=fangkun
class Neo4jConfig(BaseModel):
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"


class LLMConfig(BaseModel):
    model_name: str = "gpt-4"
    temperature: float = 0.0
    max_retries: int = 3


class EmbeddingConfig(BaseModel):
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"
    cache_dir: str = "./embedding_cache"


class Settings(BaseModel):
    neo4j: Neo4jConfig = Neo4jConfig()
    llm: LLMConfig = LLMConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()

    class Config:
        env_prefix = "MOVIE_"
        env_nested_delimiter = "__"


# 全局配置实例
settings = Settings()
# [AGC:END]
