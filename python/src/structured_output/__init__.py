# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""LangChain 结构化输出「最小可靠闭环」演示包（JSON 保证）。

分层：生成(extractor) -> 语法(json.loads) -> schema 严格校验(Pydantic)
     -> 带错误反馈重试 -> 兜底 + 观测(JSONL / 失败率计数器)
"""
# [AGC:START] tool=Cc author=fangkun
from .config import PROVIDERS, build_chat_model, resolve_provider
from .extractors import FakeExtractor, RawResult, RealExtractor
from .observability import FailureCounter, JsonlLogger
from .pipeline import Attempt, FIX_TEMPLATE, StructuredOutputPipeline
from .schemas import ContactInfo, PatientRecord, RiskLevel

__all__ = [
    "PROVIDERS",
    "Attempt",
    "FIX_TEMPLATE",
    "FakeExtractor",
    "FailureCounter",
    "JsonlLogger",
    "PatientRecord",
    "RawResult",
    "RealExtractor",
    "RiskLevel",
    "StructuredOutputPipeline",
    "build_chat_model",
    "resolve_provider",
]
# [AGC:END]
