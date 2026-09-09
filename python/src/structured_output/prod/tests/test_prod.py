# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""prod 生产级流水线单元测试（离线，无需 API key）。

运行：cd python && python -m pytest src/structured_output/prod/tests -q
覆盖：规则路由 / 模型路由解析 / 低置信度转人工 / 两层校验 /
      抽取成功 / 校验失败自修复 / 重试耗尽兜底 / 指标统计。
"""
import pytest
from langchain_core.messages import AIMessage

from src.structured_output.prod.extractor import FakeExtractor
from src.structured_output.prod.observability import ProdMetrics
from src.structured_output.prod.pipeline import ProductionPipeline
from src.structured_output.prod.router import (
    ModelRouter,
    RouteResult,
    Router,
    RuleRouter,
)
from src.structured_output.prod.schemas import (
    DocKind,
    LabReport,
    PatientRecord,
    Prescription,
)
from src.structured_output.prod.validate import (
    collect_errors,
    schema_errors,
    semantic_errors,
)

# ───────────────────────── 测试替身 ─────────────────────────
class FakeLLM:
    """返回固定 RouteChoice 的假模型，用于测 ModelRouter 解析。"""

    def __init__(self, choice: dict) -> None:
        self._choice = choice

    def with_structured_output(self, schema, **kwargs):
        self.structured_schema = schema
        return self

    def invoke(self, text: str) -> dict:
        msg = AIMessage(
            content="",
            tool_calls=[{
                "name": "RouteChoice",
                "args": dict(self._choice),
                "id": "1",
                "type": "tool_call",
            }],
        )
        return {"raw": msg, "parsed": None, "parsing_error": None}


class FakeModelRouter:
    """脚本化模型路由：模棱两可→处方(高置信)；其它→病历(低置信)。"""

    def route(self, text: str) -> RouteResult:
        if "复杂" in text:
            return RouteResult(DocKind.PRESCRIPTION, 0.9, "model", "test")
        return RouteResult(DocKind.PATIENT, 0.3, "model", "test")


FALLBACKS = {
    DocKind.PATIENT: PatientRecord(name="", age=0, symptoms=[], risk_level="low"),
    DocKind.LAB: LabReport(patient_name="", items=[]),
    DocKind.PRESCRIPTION: Prescription(patient_name="", medications=[]),
}


def make_pipeline(
    fake_mode: str = "good", *, fallbacks=FALLBACKS
) -> tuple[ProductionPipeline, ProdMetrics]:
    metrics = ProdMetrics()
    router = Router(RuleRouter(), FakeModelRouter(), threshold=0.6)
    fake = FakeExtractor(fake_mode)
    extractors = {kind: fake.bind(kind) for kind in DocKind}
    pipeline = ProductionPipeline(
        router, extractors, max_retries=2, fallbacks=fallbacks, metrics=metrics
    )
    return pipeline, metrics


# ───────────────────────── 路由 ─────────────────────────
def test_rule_router_single_hit():
    r = RuleRouter().route("患者张三发热咳嗽，评估高风险")
    assert r is not None and r.source == "rule" and r.kind == DocKind.PATIENT
    assert r.confidence == 1.0


def test_rule_router_no_hit_returns_none():
    assert RuleRouter().route("今天天气不错") is None


def test_rule_router_ambiguous_returns_none():
    # "化验"与"剂量"两个关键词同时命中 -> 模棱两可，上交模型
    assert RuleRouter().route("化验单开出处方剂量500mg") is None


def test_model_router_parses_tool_call():
    mr = ModelRouter(FakeLLM({"kind": "lab_report", "confidence": 90}))
    r = mr.route("患者化验白细胞偏高")
    assert r.source == "model" and r.kind == DocKind.LAB
    assert abs(r.confidence - 0.9) < 1e-6


def test_model_router_empty_args_is_none():
    mr = ModelRouter(FakeLLM({}))
    r = mr.route("无内容")
    assert r.kind is None


def test_router_rule_precedence():
    router = Router(RuleRouter(), ModelRouter(FakeLLM({"kind": "lab_report", "confidence": 90})))
    r = router.route("患者化验显示白细胞偏高")     # 规则命中 lab
    assert r.source == "rule" and r.kind == DocKind.LAB


def test_router_low_confidence_to_none():
    router = Router(RuleRouter(), ModelRouter(FakeLLM({"kind": "prescription", "confidence": 40})))
    r = router.route("情况复杂，需进一步检查")     # 规则零命中 -> 模型 -> 低置信
    assert r.kind is None                          # 不赌，转人工


def test_model_router_malformed_kind_does_not_crash():
    # 模型返回枚举外值（"lab" 而非 "lab_report"）-> 归一化为 kind=None，不崩溃
    mr = ModelRouter(FakeLLM({"kind": "lab", "confidence": 90}))
    r = mr.route("患者化验白细胞偏高")
    assert r.kind is None and r.reason


def test_model_router_string_confidence_no_crash():
    # 模型把置信度返回成字符串 -> 归零，不抛 TypeError
    mr = ModelRouter(FakeLLM({"kind": "lab_report", "confidence": "90"}))
    r = mr.route("患者化验白细胞偏高")
    assert r.confidence == 0.0


def test_model_router_raw_none_to_human():
    # include_raw 调用拿不到 raw -> 转人工
    class EmptyLLM:
        def with_structured_output(self, schema, **kw):
            return self

        def invoke(self, text):
            return {"raw": None, "parsed": None, "parsing_error": "boom"}

    r = ModelRouter(EmptyLLM()).route("患者化验白细胞偏高")
    assert r.kind is None


def test_router_no_model_router():
    # 规则零命中且没有模型路由 -> 定不了
    r = Router(RuleRouter(), None).route("今天天气不错")
    assert r.kind is None and r.source == "none"


# ───────────────────────── 两层校验 ─────────────────────────
def test_schema_errors_format():
    errs = schema_errors(PatientRecord, {"name": "张三", "age": 32, "symptoms": []})
    assert errs and any("risk_level" in e for e in errs)   # 缺必填字段


def test_schema_errors_extra_field():
    errs = schema_errors(PatientRecord, {
        "name": "张三", "age": 32, "symptoms": [], "risk_level": "high", "hack": 1,
    })
    assert errs and any("hack" in e for e in errs)         # extra=forbid 拦截


def test_semantic_errors_patient_age():
    obj = PatientRecord.model_validate({
        "name": "张三", "age": 200, "symptoms": ["发热"], "risk_level": "high",
    })
    errs = semantic_errors(DocKind.PATIENT, obj)
    assert any("年龄" in e for e in errs)


def test_collect_errors_two_layers():
    # 语义层错误：age=200 格式合法但业务荒谬
    errs = collect_errors(DocKind.PATIENT, PatientRecord, {
        "name": "张三", "age": 200, "symptoms": ["发热"], "risk_level": "high",
    })
    assert any("语义" in e for e in errs)


# ───────────────────────── 流水线 ─────────────────────────
def test_pipeline_rule_ok():
    pipeline, metrics = make_pipeline("good")
    obj, attempt = pipeline.invoke("患者张三发热咳嗽，评估高风险")
    assert attempt.status == "ok" and attempt.kind == DocKind.PATIENT
    assert obj is not None and obj.name == "张三"
    assert metrics.ok == 1 and metrics.validation_failures == 0


def test_pipeline_lab_ok():
    pipeline, _ = make_pipeline("good")
    obj, attempt = pipeline.invoke("患者李四化验显示白细胞偏高")
    assert attempt.status == "ok" and attempt.kind == DocKind.LAB
    assert isinstance(obj, LabReport) and obj.items


def test_pipeline_model_route_ok():
    pipeline, _ = make_pipeline("good")
    obj, attempt = pipeline.invoke("这位病人情况复杂，需进一步检查")
    # 规则零命中 -> 模型选处方(高置信) -> 抽取处方
    assert attempt.status == "ok" and attempt.kind == DocKind.PRESCRIPTION
    assert isinstance(obj, Prescription)


def test_pipeline_human_review_low_confidence():
    pipeline, metrics = make_pipeline("good")
    obj, attempt = pipeline.invoke("今天天气不错")
    # FakeModelRouter 对非"复杂"输入返回 0.3 置信 -> 转人工
    assert attempt.status == "human_review" and obj is None
    assert metrics.human == 1


def test_pipeline_retry_self_heal():
    pipeline, metrics = make_pipeline("retry_once")
    obj, attempt = pipeline.invoke("患者张三发热咳嗽")
    assert attempt.status == "ok"
    assert attempt.attempts_used == 2                  # 第 1 次失败,第 2 次成功
    assert obj is not None and obj.symptoms             # 语义层症状非空才通过
    assert metrics.validation_failures >= 1


def test_pipeline_hopeless_fallback():
    pipeline, metrics = make_pipeline("hopeless")
    obj, attempt = pipeline.invoke("患者张三发热咳嗽")
    assert attempt.status == "fallback"                 # 兜底状态与"ok"区分
    assert isinstance(obj, PatientRecord) and obj.symptoms == []   # 默认空病历
    assert attempt.attempts_used == 3                   # 1 + max_retries=2
    assert metrics.fallback == 1


def test_pipeline_hopeless_no_fallback_human():
    pipeline, _ = make_pipeline("hopeless", fallbacks=None)
    obj, attempt = pipeline.invoke("患者张三发热咳嗽")
    assert attempt.status == "human_review" and obj is None
    assert attempt.errors                  # 记录了重试耗尽原因


def test_pipeline_nojson_fallback():
    # 模型只会说人话、不吐 JSON -> 语法层失败 -> 重试耗尽 -> 业务兜底
    pipeline, metrics = make_pipeline("nojson")
    obj, attempt = pipeline.invoke("患者张三发热咳嗽")
    assert attempt.status == "fallback" and isinstance(obj, PatientRecord)
    assert attempt.attempts_used == 3      # 1 + max_retries=2
    assert metrics.validation_failures == 3


# ───────────────────────── 指标 ─────────────────────────
def test_metrics_summary():
    metrics = ProdMetrics()
    metrics.record_route("rule", 1.0)
    metrics.record_route("model", 0.3)
    metrics.record_validation(ok=True)
    metrics.record_validation(ok=False)
    metrics.record_result(ok=True, attempts_used=2)
    s = metrics.summary()
    assert s["total"] == 1 and s["ok"] == 1 and s["success_rate_%"] == 100.0
    assert s["route_source"] == {"rule": 1, "model": 1}
    assert s["low_confidence"] == 1 and s["validation_failures"] == 1
