# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""运行入口（在仓库 python/ 目录下执行）：

  离线演示（无需 API key）：python -m src.structured_output.demo --fake
  离线自检（含真实 extractor 构造）：python -m src.structured_output.demo --self-check
  真实调用：python -m src.structured_output.demo --provider qwen --method function_calling

  也支持 IDE 直接运行 demo.py：脚本会自动把仓库 python/ 目录加入 sys.path。
"""
import argparse
import os
import sys

# 直接运行 demo.py（如 PyCharm Run 按钮）时 __package__ 为空、没有父包上下文，
# 需手动把仓库 python/ 目录加入 sys.path 才能按绝对路径导入 src.structured_output.*;
# 通过 `python -m src.structured_output.demo` 运行时 __package__ 非空，跳过该步。
if __package__ in (None, ""):
    sys.path.insert(
        0,
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    )

from dotenv import load_dotenv

from src.structured_output.config import PROVIDERS, build_chat_model, resolve_provider
from src.structured_output.extractors import FakeExtractor, RealExtractor
from src.structured_output.observability import FailureCounter, JsonlLogger
from src.structured_output.pipeline import StructuredOutputPipeline
from src.structured_output.schemas import PatientRecord

# [AGC:START] tool=Cc author=fangkun
SAMPLE_TEXTS = {
    "完整病历": "患者老四，90岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13333333333。",
    # "信息缺失": "一个发烧的病人。",
    # "无关内容": "今天天气不错，适合出门散步。",
}


def _run_case(pipeline: StructuredOutputPipeline, label: str, text: str) -> None:
    print(f"\n=== {label} ===")
    print(f"输入: {text[:60]}")
    obj, attempt = pipeline.invoke(text)
    print(f"status={attempt.status}  attempts={attempt.attempts_used}  latency={attempt.latency_ms}ms")
    for err in attempt.errors:
        print(f"  [err] {err[:160]}")
    print(f"结果: {obj.model_dump() if obj else None}")


def run_fake_demo() -> None:
    """四种脚本化行为，完整演示成功 / 自修复 / 兜底 / 无 JSON 四条路径。"""
    for mode in ("good", "retry_once", "hopeless", "nojson"):
        counter = FailureCounter()
        pipeline = StructuredOutputPipeline(
            FakeExtractor(mode),
            PatientRecord,
            max_retries=2,
            logger=JsonlLogger(),
            counter=counter,
            provider="fake",
            model=f"fake:{mode}",
            method="fake",
        )
        print(f"\n############ 假模型模式：{mode} ############")
        for label, text in SAMPLE_TEXTS.items():
            _run_case(pipeline, label, text)
        print(f"\n计数: {counter.summary()}")


def run_real_demo(provider: str, method: str) -> None:
    """真实调用：走 with_structured_output + 校验 / 重试 / 兜底闭环。"""
    name = resolve_provider(provider)
    cfg = PROVIDERS[name]
    llm = build_chat_model(provider)
    counter = FailureCounter()
    pipeline = StructuredOutputPipeline(
        RealExtractor(llm, PatientRecord, method),
        PatientRecord,
        max_retries=2,
        logger=JsonlLogger(),
        counter=counter,
        provider=name,
        model=cfg["model"],
        method=method,
    )
    for label, text in SAMPLE_TEXTS.items():
        _run_case(pipeline, label, text)
    print(f"\n计数: {counter.summary()}")


def self_check() -> None:
    """离线自检：验证真实 extractor 能构造（无需 key），再跑一遍全流水线。"""
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model="deepseek-v4-flash",
        base_url="https://example.invalid",
        api_key="dummy",  # 仅用于构造，不发起网络请求
    )
    for method in ("function_calling", "json_mode"):
        RealExtractor(llm, PatientRecord, method)
        print(f"[构造通过] RealExtractor method={method}")
    run_fake_demo()


def main() -> None:
    # Windows 控制台默认 GBK，强制 UTF-8 输出避免中文乱码
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="LangChain 结构化输出最小可靠闭环演示")
    parser.add_argument("--fake", action="store_true", help="离线假模型演示（无需 API key）")
    parser.add_argument("--self-check", action="store_true", help="离线自检")
    parser.add_argument("--provider", default="auto", choices=["auto", "qwen", "deepseek"])
    parser.add_argument(
        "--method",
        default="function_calling",
        choices=["function_calling", "json_mode"],
    )
    args = parser.parse_args()

    if args.self_check:
        self_check()
    elif args.fake:
        run_fake_demo()
    else:
        run_real_demo(args.provider, args.method)


if __name__ == "__main__":
    main()
# [AGC:END]
