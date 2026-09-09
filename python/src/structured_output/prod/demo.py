# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""生产级流水线演示入口（在仓库 python/ 目录下执行）：

  离线演示（无需 API key）：python -m src.structured_output.prod.demo --fake
  真实调用：python -m src.structured_output.prod.demo

  --fake 用 FakeModelRouter + FakeExtractor 覆盖流水线所有分支：
    规则命中三类 / 模棱两可走模型选择题 / 低置信度转人工 / 校验失败自修复 / 重试耗尽兜底。
"""
import argparse
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(
        0,
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    )

from dotenv import load_dotenv

from src.structured_output.config import build_chat_model
from src.structured_output.prod.extractor import FakeExtractor, SchemaExtractor
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
    SCHEMA_BY_KIND,
)

# [AGC:START] tool=Cc author=fangkun
DEFAULT_FALLBACKS = {
    DocKind.PATIENT: PatientRecord(name="", age=0, symptoms=[], risk_level="low"),
    DocKind.LAB: LabReport(patient_name="", items=[]),
    DocKind.PRESCRIPTION: Prescription(patient_name="", medications=[]),
}


class FakeModelRouter:
    """脚本化模型路由：只覆盖低置信度/模棱两可两条路，让离线演示跑通全流程。"""

    def route(self, text: str) -> RouteResult:
        if "天气" in text:
            return RouteResult(None, 0.3, "model", "低置信度(30%)不赌，转人工")
        if "复杂" in text or "进一步" in text:
            return RouteResult(DocKind.PRESCRIPTION, 0.9, "model", "模型判为处方")
        return RouteResult(DocKind.PATIENT, 0.85, "model", "模型判为病历")


SAMPLES = {
    "病历·规则命中": "患者张三，32岁，发热咳嗽，评估高风险，电话13800000000",
    "化验单·规则命中": "患者李四，化验显示白细胞偏高，体温39度",
    "处方·规则命中": "开具处方，阿莫西林500mg，一日两次，饭后服用",
    "模棱两可·走模型选择题": "这位病人情况复杂，需进一步检查",
    "低置信度·转人工": "今天天气不错，适合出门散步",
}


def _make_fake_pipeline(fake_mode: str) -> tuple[ProductionPipeline, ProdMetrics]:
    metrics = ProdMetrics()
    router = Router(RuleRouter(), FakeModelRouter(), threshold=0.6)
    fake = FakeExtractor(fake_mode)
    extractors = {kind: fake.bind(kind) for kind in DocKind}
    pipeline = ProductionPipeline(
        router, extractors, max_retries=2, fallbacks=DEFAULT_FALLBACKS, metrics=metrics
    )
    return pipeline, metrics


def _run_case(pipeline: ProductionPipeline, label: str, text: str) -> None:
    print(f"\n=== {label} ===")
    print(f"输入: {text[:50]}")
    obj, attempt = pipeline.invoke(text)
    print(
        f"route={attempt.route.source}:{attempt.route.reason}  "
        f"kind={attempt.kind.value if attempt.kind else None}  "
        f"status={attempt.status}  attempts={attempt.attempts_used}  "
        f"latency={attempt.latency_ms}ms"
    )
    for err in attempt.errors[:3]:
        print(f"  [err] {err[:120]}")
    print(f"结果: {obj.model_dump() if obj else None}")


def run_fake_demo() -> None:
    print("############ 路径 1：一路顺利（good）############")
    pipeline, metrics = _make_fake_pipeline("good")
    for label, text in SAMPLES.items():
        _run_case(pipeline, label, text)
    print(f"\n计数: {metrics.summary()}")

    print("\n\n############ 路径 2：校验失败一次后自修复（retry_once）############")
    pipeline, _ = _make_fake_pipeline("retry_once")
    _run_case(pipeline, "病历·首次校验失败", SAMPLES["病历·规则命中"])
    print("\n\n############ 路径 3：重试耗尽走业务兜底（hopeless）############")
    pipeline, _ = _make_fake_pipeline("hopeless")
    _run_case(pipeline, "病历·反复校验失败", SAMPLES["病历·规则命中"])


def run_real_demo(provider: str) -> None:
    llm = build_chat_model(provider)
    metrics = ProdMetrics()
    router = Router(RuleRouter(), ModelRouter(llm), threshold=0.6)
    extractors = {
        kind: SchemaExtractor(llm, SCHEMA_BY_KIND[kind]) for kind in DocKind
    }
    pipeline = ProductionPipeline(
        router, extractors, max_retries=2, fallbacks=DEFAULT_FALLBACKS, metrics=metrics
    )
    for label, text in SAMPLES.items():
        _run_case(pipeline, label, text)
    print(f"\n计数: {metrics.summary()}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="生产级结构化输出流水线演示")
    parser.add_argument("--fake", action="store_true", help="离线演示（无需 API key）")
    parser.add_argument("--provider", default="auto", choices=["auto", "qwen", "deepseek"])
    args = parser.parse_args()

    if args.fake:
        run_fake_demo()
    else:
        run_real_demo(args.provider)


if __name__ == "__main__":
    main()
# [AGC:END]
