# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""prod_pure 生产级流水线（纯 Python 版）单元测试（离线，无需 API key）。

运行：cd python && python -m pytest src/base_practice/20_prod_structured_output/tests -q
覆盖：规则路由 / 模型路由解析 / 低置信度转人工 / 两层校验 /
      抽取成功 / 校验失败自修复 / 重试耗尽兜底 / 指标统计。
"""
import json
import sys
import urllib.error
from pathlib import Path

# 目录名以数字开头无法 `import`/`python -m`：把实践目录插进 sys.path，扁平导入兄弟模块
_MODULE_DIR = Path(__file__).resolve().parent.parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

import pytest

import prod_pure as m
from prod_pure import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_FALLBACKS,
    DocKind,
    FakeExtractor,
    ModelRouter,
    ProdMetrics,
    ProductionPipeline,
    RawResult,
    RouteResult,
    Router,
    RuleRouter,
    SCHEMA_BY_KIND,
    collect_errors,
    schema_errors,
    semantic_errors,
)

_USE_DEFAULT = object()     # make_pipeline 哨兵：区分"用默认兜底"与"显式不兜底(None)"


class FakeModelRouter:
    """脚本化模型路由：模棱两可→处方(高置信)；其它→病历(低置信)。"""

    def route(self, text: str) -> RouteResult:
        if "复杂" in text:
            return RouteResult(DocKind.PRESCRIPTION, 0.9, "model", "test")
        return RouteResult(DocKind.PATIENT, 0.3, "model", "test")


def make_pipeline(fake_mode: str = "good", *, fallbacks=_USE_DEFAULT):
    metrics = ProdMetrics()
    router = Router(RuleRouter(), FakeModelRouter(), threshold=DEFAULT_CONFIDENCE_THRESHOLD)
    fake = FakeExtractor(fake_mode)
    extractors = {kind: fake.bind(kind) for kind in DocKind}
    if fallbacks is _USE_DEFAULT:
        fallbacks = DEFAULT_FALLBACKS
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


def test_model_router_parses_tool_call(monkeypatch):
    monkeypatch.setattr(m, "extract_json",
                        lambda payload: RawResult(json.dumps({"kind": "lab_report", "confidence": 90})))
    r = ModelRouter().route("患者化验白细胞偏高")
    assert r.source == "model" and r.kind == DocKind.LAB
    assert abs(r.confidence - 0.9) < 1e-6


def test_model_router_empty_args_is_none(monkeypatch):
    monkeypatch.setattr(m, "extract_json", lambda payload: RawResult(json.dumps({})))
    r = ModelRouter().route("无内容")
    assert r.kind is None


def test_model_router_malformed_kind_does_not_crash(monkeypatch):
    # 模型返回枚举外值（"lab" 而非 "lab_report"）-> 归一化为 kind=None，不崩溃
    monkeypatch.setattr(m, "extract_json",
                        lambda payload: RawResult(json.dumps({"kind": "lab", "confidence": 90})))
    r = ModelRouter().route("患者化验白细胞偏高")
    assert r.kind is None and r.reason


def test_model_router_string_confidence_no_crash(monkeypatch):
    # 模型把置信度返回成字符串 -> 归零，不抛 TypeError
    monkeypatch.setattr(m, "extract_json",
                        lambda payload: RawResult(json.dumps({"kind": "lab_report", "confidence": "90"})))
    r = ModelRouter().route("患者化验白细胞偏高")
    assert r.confidence == 0.0


def test_model_router_network_error_no_crash(monkeypatch):
    # 网络异常 -> 转人工，不崩溃
    def boom(payload):
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(m, "extract_json", boom)
    r = ModelRouter().route("患者化验白细胞偏高")
    assert r.kind is None and "异常" in r.reason


def test_router_rule_precedence():
    # 规则命中即判，模型不应被调用
    class Boom:
        def route(self, text):
            raise AssertionError("规则命中不应再调模型")

    router = Router(RuleRouter(), Boom())
    r = router.route("患者化验显示白细胞偏高")
    assert r.source == "rule" and r.kind == DocKind.LAB


def test_router_low_confidence_to_none():
    class LowConf:
        def route(self, text):
            return RouteResult(DocKind.PRESCRIPTION, 0.4, "model", "低置信")

    router = Router(RuleRouter(), LowConf(), threshold=0.6)
    r = router.route("情况复杂，需进一步检查")
    assert r.kind is None


def test_router_no_model_router():
    # 规则零命中且没有模型路由 -> 定不了
    r = Router(RuleRouter(), None).route("今天天气不错")
    assert r.kind is None and r.source == "none"


# ───────────────────────── 两层校验 ─────────────────────────
PATIENT = SCHEMA_BY_KIND[DocKind.PATIENT]


def test_schema_errors_format():
    errs = schema_errors(PATIENT, {"name": "张三", "age": 32, "symptoms": []})
    assert errs and any("risk_level" in e for e in errs)   # 缺必填字段


def test_schema_errors_extra_field():
    errs = schema_errors(PATIENT, {
        "name": "张三", "age": 32, "symptoms": [], "risk_level": "high", "hack": 1,
    })
    assert errs and any("hack" in e for e in errs)         # additionalProperties:false 拦截


def test_schema_errors_enum():
    errs = schema_errors(PATIENT, {
        "name": "张三", "age": 32, "symptoms": [], "risk_level": "SEVERE",
    })
    assert errs and any("枚举" in e for e in errs)          # 枚举外值拦截


def test_schema_errors_nested_contact_extra():
    # 嵌套对象递归：contact 里多一个字段也要被拦
    errs = schema_errors(PATIENT, {
        "name": "张三", "age": 32, "symptoms": [], "risk_level": "low",
        "contact": {"phone": "13800000000", "hack": 1},
    })
    assert errs and any("contact.hack" in e for e in errs)


def test_schema_errors_array_item_type():
    # 数组元素类型：symptoms 里混进数字
    errs = schema_errors(PATIENT, {
        "name": "张三", "age": 32, "symptoms": ["发热", 123], "risk_level": "low",
    })
    assert errs and any("symptoms[1]" in e for e in errs)


def test_schema_errors_null_union():
    # X | None 联合类型：contact 必须是对象或 null，数字不行
    errs = schema_errors(PATIENT, {
        "name": "张三", "age": 32, "symptoms": [], "risk_level": "low", "contact": 123,
    })
    assert errs and any("contact" in e for e in errs)


def test_schema_errors_bool_not_int():
    # bool 不是 integer：age: true 必须拒绝
    errs = schema_errors(PATIENT, {
        "name": "张三", "age": True, "symptoms": [], "risk_level": "low",
    })
    assert errs and any("age" in e for e in errs)


def test_semantic_errors_patient_age():
    errs = semantic_errors(DocKind.PATIENT, {
        "name": "张三", "age": 200, "symptoms": ["发热"], "risk_level": "high",
    })
    assert any("年龄" in e for e in errs)


def test_collect_errors_two_layers():
    # 语义层错误：age=200 格式合法但业务荒谬
    errs = collect_errors(DocKind.PATIENT, PATIENT, {
        "name": "张三", "age": 200, "symptoms": ["发热"], "risk_level": "high",
    })
    assert any("语义" in e for e in errs)


def test_collect_errors_schema_wins_over_semantic():
    # 格式错误优先返回，不跑语义（age 缺失时语义层 data["age"] 会 KeyError，不应被执行）
    errs = collect_errors(DocKind.PATIENT, PATIENT, {
        "name": "张三", "symptoms": [], "risk_level": "high",
    })
    assert errs and any("age" in e for e in errs)


# ───────────────────────── 流水线 ─────────────────────────
def test_pipeline_rule_ok():
    pipeline, metrics = make_pipeline("good")
    obj, attempt = pipeline.invoke("患者张三发热咳嗽，评估高风险")
    assert attempt.status == "ok" and attempt.kind == DocKind.PATIENT
    assert obj is not None and obj["name"] == "张三"
    assert metrics.ok == 1 and metrics.validation_failures == 0


def test_pipeline_lab_ok():
    pipeline, _ = make_pipeline("good")
    obj, attempt = pipeline.invoke("患者李四化验显示白细胞偏高")
    assert attempt.status == "ok" and attempt.kind == DocKind.LAB
    assert isinstance(obj, dict) and obj["items"]


def test_pipeline_model_route_ok():
    pipeline, _ = make_pipeline("good")
    obj, attempt = pipeline.invoke("这位病人情况复杂，需进一步检查")
    # 规则零命中 -> 模型选处方(高置信) -> 抽取处方
    assert attempt.status == "ok" and attempt.kind == DocKind.PRESCRIPTION
    assert isinstance(obj, dict) and obj["medications"]


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
    assert obj is not None and obj["symptoms"]          # 语义层症状非空才通过
    assert metrics.validation_failures >= 1


def test_pipeline_hopeless_fallback():
    pipeline, metrics = make_pipeline("hopeless")
    obj, attempt = pipeline.invoke("患者张三发热咳嗽")
    assert attempt.status == "fallback"                 # 兜底状态与"ok"区分
    assert isinstance(obj, dict) and obj["symptoms"] == []   # 默认空病历
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
    assert attempt.status == "fallback" and isinstance(obj, dict)
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
