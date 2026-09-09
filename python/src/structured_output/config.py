# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""Provider 配置：deepseek / qwen 均走 OpenAI 兼容接口，用 ChatOpenAI 统一建模。"""
import os
from typing import Any

from langchain_openai import ChatOpenAI

# [AGC:START] tool=Cc author=fangkun
PROVIDERS: dict[str, dict[str, Any]] = {
    "qwen": {
        "base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "model": "qwen3.6-plus",
        # qwen 系列默认开启 thinking，会限制 tool_choice 导致结构化输出 400 错误，必须显式关闭
        "extra_body": {"enable_thinking": False},
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "extra_body": None,
    },
}


def resolve_provider(name: str) -> str:
    """把 "auto" 解析为具体 provider：按环境变量/模型名启发式判断。"""
    if name != "auto":
        return name
    model = os.environ.get("OPENAI_MODEL", "").lower()
    base = os.environ.get("OPENAI_BASE_URL", "").lower()
    if "deepseek" in model or "deepseek" in base:
        return "deepseek"
    if "glm-5.2" in model or "deepseek" in base:
        return "deepseek"
    if "qwen" in model or "dashscope" in base:
        return "qwen"
    return "qwen"


def build_chat_model(provider: str = "auto") -> ChatOpenAI:
    """构建指向 OpenAI 兼容接口的 ChatOpenAI；env 变量可覆盖 provider 默认值。

    max_tokens 默认不传：qwen json_object 模式下设置 max_tokens 可能截断输出导致坏 JSON；
    除非 .env 显式配置 OPENAI_MAX_TOKENS（如 20000），否则交给 provider 默认值。
    """
    name = resolve_provider(provider)
    cfg = PROVIDERS[name]
    max_tokens = os.environ.get("OPENAI_MAX_TOKENS")
    return ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", cfg["model"]),
        base_url=os.environ.get("OPENAI_BASE_URL", cfg["base_url"]),
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0")),
        max_tokens=int(max_tokens) if max_tokens else None,
        # qwen 的 enable_thinking 必须走 extra_body：直接展开进构造参数会进 model_kwargs
        # -> payload 顶层，新版 openai SDK 强类型签名会抛 TypeError
        extra_body=cfg["extra_body"],
    )
# [AGC:END]
