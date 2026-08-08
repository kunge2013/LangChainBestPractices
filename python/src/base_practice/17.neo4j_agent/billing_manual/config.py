# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual.config
=====================
Unified configuration dataclass.

All Neo4j / LLM / embedding / retrieval settings in one place.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# [AGC:START] tool=Cc author=fangkun


@dataclass
class Config:
    """Unified configuration for the billing_manual package."""

    # ── Document paths ──────────────────────────────────────────────────────
    billing_manual_path: str = field(
        default_factory=lambda: str(
            Path(__file__).resolve().parent.parent / "操作手册.docx"
        )
    )
    images_output_dir: str = field(
        default_factory=lambda: str(
            Path(__file__).resolve().parent.parent / "output" / "images"
        )
    )

    # ── Neo4j ───────────────────────────────────────────────────────────────
    vector_index_name: str = "billing_manual_vectors"
    neo4j_uri: str = field(default_factory=lambda: os.environ.get("NEO4J_URI", ""))
    neo4j_username: str = field(default_factory=lambda: os.environ.get("NEO4J_USERNAME", ""))
    neo4j_password: str = field(default_factory=lambda: os.environ.get("NEO4J_PASSWORD", ""))
    neo4j_database: str = field(
        default_factory=lambda: os.environ.get("NEO4J_DATABASE", "neo4j")
    )

    # ── Startup behaviour ───────────────────────────────────────────────────
    init_on_startup: bool = field(
        default_factory=lambda: os.environ.get("INIT_ON_STARTUP", "true").lower() == "true"
    )

    # ── Embedding ───────────────────────────────────────────────────────────
    embedding_model: str = "shibing624/text2vec-base-chinese"
    embedding_device: str = "cpu"

    # ── Text chunking ───────────────────────────────────────────────────────
    chunk_size: int = 1500
    chunk_overlap: int = 300

    # ── Retrieval ───────────────────────────────────────────────────────────
    search_k: int = 3
    image_base_url: str = field(
        default_factory=lambda: os.environ.get("IMAGE_BASE_URL", "http://localhost:2024")
    )

    # ── LLM (OpenAI-compatible) ─────────────────────────────────────────────
    openai_model: str = field(
        default_factory=lambda: os.environ.get("OPENAI_MODEL", "qwen3.5-plus")
    )
    openai_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
    )
    openai_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )
    openai_temperature: float = field(
        default_factory=lambda: float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))
    )
    openai_max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("OPENAI_MAX_TOKENS", "2000"))
    )
    describe_image_max_tokens: int = 102400
    describe_max_retries: int = 3

    # ── Helper methods ──────────────────────────────────────────────────────

    def get_neo4j_params(self) -> dict:
        return {
            "url": self.neo4j_uri,
            "username": self.neo4j_username,
            "password": self.neo4j_password,
            "database": self.neo4j_database,
        }

    def get_llm_params(self) -> dict:
        return {
            "model": self.openai_model,
            "base_url": self.openai_base_url,
            "api_key": self.openai_api_key,
            "temperature": self.openai_temperature,
            "max_tokens": self.openai_max_tokens,
        }

# [AGC:END]
