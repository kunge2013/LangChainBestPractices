# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual.agent.pipeline
==============================
End-to-end pipeline: parse → describe → build vector store → create agent.

Also provides ``build_agent()`` for LangGraph API integration.

Adapted from 3.billing_manual_agent.py :: BillingManualPipeline, build_agent.

NOTE
----
This module does NOT execute ``build_agent()`` at import time.
Callers must invoke ``build_agent()`` explicitly.
"""

import logging
from typing import Any

from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector

from ..config import Config
from ..document.describer import ImageDescriber
from ..document.parser import DocxParser
from ..knowledge.vectorstore import VectorStoreBuilder
from ..models import ImageElement
from .agent import BillingAgent

logger = logging.getLogger(__name__)

# [AGC:START] tool=Cc author=fangkun


class BillingManualPipeline:
    """Full pipeline: parse → describe → chunk → build vector store → create agent."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()

    def build(self, force_recreate: bool = False) -> tuple[Neo4jVector, BillingAgent]:
        # Stage 1: parse .docx
        self._log_stage(1, "解析 .docx 文档")
        parser = DocxParser(self.config)
        elements = parser.parse(self.config.billing_manual_path)

        # Stage 2: generate image descriptions (first 3 images only, per original)
        self._log_stage(2, "生成图片描述")

        # 图片描述暂时没有用注释掉
        # describer = ImageDescriber(self.config)
        # images = [e for e in elements if isinstance(e, ImageElement)]
        # describer.describe_batch(images)

        # Stage 3: build vector store
        self._log_stage(3, "构建向量库")
        store_builder = VectorStoreBuilder(self.config)
        docs = store_builder.build_documents(elements)
        db = store_builder.build(docs, force_recreate)

        # Stage 4: create agent
        self._log_stage(4, "创建 Agent")
        agent = BillingAgent(self.config, db)
        agent.create()

        return db, agent

    @staticmethod
    def _log_stage(stage: int, name: str) -> None:
        sep = "=" * 50
        logger.info(sep)
        logger.info("阶段 %d: %s", stage, name)
        logger.info(sep)


def build_agent() -> Any:
    """LangGraph API agent factory.

    Honours ``Config.init_on_startup``:
    - True  → run the full pipeline (parse → describe → build store)
    - False → connect to existing vector store only
    """
    config = Config()

    if config.init_on_startup:
        pipeline = BillingManualPipeline(config)
        _, billing_agent = pipeline.build(force_recreate=True)
        return billing_agent.agent
    else:
        store_builder = VectorStoreBuilder(config)
        db = store_builder.build([], force_recreate=False)
        billing_agent = BillingAgent(config, db)
        billing_agent.create()
        return billing_agent.agent

# [AGC:END]
