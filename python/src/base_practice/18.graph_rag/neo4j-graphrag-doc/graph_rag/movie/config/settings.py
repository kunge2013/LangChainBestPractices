# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
配置模块
从项目根目录 python/.env 读取配置
支持 OpenAI 协议（dashscope 等兼容 API）
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv


# [AGC:START] tool=Cc author=fangkun

# 加载 python/.env 文件
load_dotenv()


class Neo4jConfig(BaseModel):
    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username: str = os.getenv("NEO4J_USERNAME", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "password")
    database: str = os.getenv("NEO4J_DATABASE", "neo4j")


class LLMConfig(BaseModel):
    """LLM 配置，使用 OpenAI 协议，支持 dashscope 等兼容 API"""
    base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = os.getenv("OPENAI_MODEL", "gpt-4")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "20000"))


@dataclass
class EmbeddingConfig:
    """Embedding 配置，使用 HuggingFace 本地模型"""
    model_name: str = os.getenv("HF_EMBEDDING_MODEL", "shibing624/text2vec-base-chinese")
    device: str = os.getenv("HF_EMBEDDING_DEVICE", "cpu")
    cache_dir: str = field(
        default_factory=lambda: os.environ.get(
            "HF_HOME", r"C:\Users\ThinkPad\.cache\huggingface"
        )
    )


class Settings(BaseModel):
    neo4j: Neo4jConfig = Neo4jConfig()
    llm: LLMConfig = LLMConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()

    class Config:
        arbitrary_types_allowed = True


# 全局配置实例
settings = Settings()
# [AGC:END]
