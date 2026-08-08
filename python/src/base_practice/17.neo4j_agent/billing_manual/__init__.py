# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual
===============
操作手册多模态知识检索 Agent 包。

将 .docx 操作手册解析为文本+图片，用 VL 模型生成图片描述，
存入 Neo4j 向量库，提供 deep_agent 检索接口。

公共 API
--------
Config, TextElement, ImageElement
BillingManualError, DocumentParseError, ImageDescribeError, VectorStoreError
DocxParser, ImageDescriber
VectorStoreBuilder, KnowledgeSearcher, GetSectionImages
BillingAgent, BillingManualPipeline, build_agent

用法
----
    >>> from billing_manual import build_agent
    >>> agent = build_agent()

    >>> from billing_manual import BillingManualPipeline, Config
    >>> pipeline = BillingManualPipeline(Config())
    >>> db, agent = pipeline.build(force_recreate=True)
"""

from .agent import BillingAgent, BillingManualPipeline, build_agent
from .config import Config
from .document import DocxParser, ImageDescriber
from .exceptions import (
    BillingManualError,
    DocumentParseError,
    ImageDescribeError,
    VectorStoreError,
)
from .knowledge import GetSectionImages, KnowledgeSearcher, VectorStoreBuilder
from .models import ImageElement, TextElement

__all__ = [
    # config & models
    "Config",
    "TextElement",
    "ImageElement",
    # exceptions
    "BillingManualError",
    "DocumentParseError",
    "ImageDescribeError",
    "VectorStoreError",
    # document
    "DocxParser",
    "ImageDescriber",
    # knowledge
    "VectorStoreBuilder",
    "KnowledgeSearcher",
    "GetSectionImages",
    # agent
    "BillingAgent",
    "BillingManualPipeline",
    "build_agent",
]
