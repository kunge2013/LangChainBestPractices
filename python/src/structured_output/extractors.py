# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""生成层抽象：把『模型输出』规范化为『JSON 字符串』。

- RealExtractor：真实调用 with_structured_output(include_raw=True)
- FakeExtractor：离线脚本化四种行为，无 API key 也能演示重试/兜底/观测
"""
import json
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

# [AGC:START] tool=Cc author=fangkun
@dataclass
class RawResult:
    """抽取结果：json_str 为可解析的 JSON 字符串；为空时 note 说明原因。

    raw_message 保存模型的原始响应结构（AIMessage 序列化），供日志记录完整响应。
    """
    json_str: str | None
    note: str = ""
    raw_message: dict | None = None


def _serialize_message(raw: BaseMessage) -> dict | None:
    """把 AIMessage 序列化成可 JSON 化的 dict（tool_calls / response_metadata / usage 等）。"""
    try:
        return raw.model_dump()
    except Exception:
        return {"content": getattr(raw, "content", None)}


def _strip_json(content: str) -> str | None:
    """从模型文本里抠出第一个 JSON 对象，容忍 ```json 围栏和前导文本。"""
    text = content.strip()
    if text.startswith("```"):
        first = text.find("\n")
        last = text.rfind("```")
        if first != -1 and last != -1 and last > first:
            text = text[first + 1:last].strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start:end + 1]


class RealExtractor:
    """用 LangChain 1.x 的 with_structured_output() 产出结构化响应。"""

    def __init__(self, llm: BaseChatModel, schema: type[BaseModel], method: str) -> None:
        self.method = method
        # include_raw=True：保留原始消息，由本包自己负责最终严格校验
        self._runnable = llm.with_structured_output(schema, method=method, include_raw=True)

    def extract(self, text: str) -> RawResult:
        res: dict[str, Any] = self._runnable.invoke(text)
        raw: BaseMessage | None = res.get("raw")
        if raw is None:
            return RawResult(None, "无原始输出", None)
        json_str, note = self._pick_json(raw)
        return RawResult(json_str, note, _serialize_message(raw))

    @staticmethod
    def _pick_json(raw: BaseMessage) -> tuple[str | None, str]:
        """从 AIMessage 里提取 JSON：function_calling 取 tool_calls[0].args，否则取 content。"""
        tool_calls = getattr(raw, "tool_calls", None)
        if tool_calls:
            args = tool_calls[0].get("args") if isinstance(tool_calls[0], dict) else None
            if isinstance(args, dict) and args:
                return json.dumps(args, ensure_ascii=False), ""
        content = getattr(raw, "content", None)
        if isinstance(content, str) and content.strip():
            body = _strip_json(content)
            if body:
                return body, ""
            return None, "content 中未找到 JSON 对象"
        return None, "模型未返回工具调用或文本内容"


class FakeExtractor:
    """离线假抽取器：脚本化四种行为，覆盖流水线的所有分支。"""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    def extract(self, text: str) -> RawResult:
        good = RawResult(
            json.dumps(
                {
                    "name": "张三",
                    "age": 32,
                    "symptoms": ["发热", "咳嗽"],
                    "risk_level": "high",
                    "contact": {"phone": "13800000000"},
                },
                ensure_ascii=False,
            )
        )
        if self.mode == "good":
            return good
        if self.mode == "retry_once":
            # 首次返回非法 JSON（缺必填 name、age 为字符串、枚举值非法）；
            # prompt 带上"未通过校验"的错误反馈后返回合法 JSON -> 演示自修复
            if "未通过校验" in text:
                return good
            return RawResult(
                json.dumps(
                    {"age": "32", "symptoms": [], "risk_level": "SEVERE"},
                    ensure_ascii=False,
                )
            )
        if self.mode == "hopeless":
            # 永远返回非法 JSON -> 演示重试耗尽后的兜底
            return RawResult(json.dumps({"name": "?"}, ensure_ascii=False))
        # nojson：返回纯文本 -> 演示 JSON 语法层失败
        return RawResult(None, "抱歉，我只能返回纯文本。")
# [AGC:END]
