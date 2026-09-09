# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""生成层：对选中的单一 schema 做结构化抽取。

- pick_json       从 AIMessage 里取 JSON（function_calling 走 tool_calls，否则 content）
- SchemaExtractor 真实：with_structured_output(include_raw=True)
- FakeExtractor   测试：按 kind 脚本化生成合法/非法 JSON，离线跑全流水线
"""
import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from .schemas import DocKind

# [AGC:START] tool=Cc author=fangkun
@dataclass
class RawResult:
    """抽取结果：json_str 为可解析的 JSON 字符串；为空时 note 说明原因。"""
    json_str: str | None
    note: str = ""


def pick_json(raw: BaseMessage) -> tuple[str | None, str]:
    """从 AIMessage 提取 JSON：function_calling 取 tool_calls[0].args，否则取 content。"""
    tool_calls = getattr(raw, "tool_calls", None)
    if tool_calls:
        args = tool_calls[0].get("args") if isinstance(tool_calls[0], dict) else None
        if isinstance(args, dict) and args:
            return json.dumps(args, ensure_ascii=False), ""
    content = getattr(raw, "content", None)
    if isinstance(content, str) and content.strip():
        text = content.strip()
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1], ""
        return None, "content 中未找到 JSON 对象"
    return None, "模型未返回工具调用或文本内容"


class SchemaExtractor:
    """单一 schema 的结构化抽取器：每类文档一个实例，一次只干一件事。"""

    def __init__(
        self,
        llm: Any,
        model_cls: type[BaseModel],
        *,
        method: str = "function_calling",
    ) -> None:
        self.model_cls = model_cls
        self._runnable = llm.with_structured_output(
            model_cls, method=method, include_raw=True
        )

    def extract(self, text: str) -> RawResult:
        res = self._runnable.invoke(text)
        raw = res.get("raw")
        if raw is None:
            return RawResult(None, "无原始输出")
        json_str, note = pick_json(raw)
        return RawResult(json_str, note)


# 每个 kind 一份合法 JSON，供 FakeExtractor 与测试使用
_GOOD_BY_KIND: dict[DocKind, dict] = {
    DocKind.PATIENT: {
        "name": "张三",
        "age": 32,
        "symptoms": ["发热", "咳嗽"],
        "risk_level": "high",
        "contact": {"phone": "13800000000"},
    },
    DocKind.LAB: {
        "patient_name": "张三",
        "items": [{"name": "白细胞", "value": 12.3, "unit": "10^9/L", "flag": "偏高"}],
        "conclusion": "白细胞偏高",
    },
    DocKind.PRESCRIPTION: {
        "patient_name": "张三",
        "medications": [{"name": "阿莫西林", "dosage": "500mg", "frequency": "一日两次"}],
        "notes": "饭后服用",
    },
}

_BAD_BY_KIND: dict[DocKind, dict] = {
    DocKind.PATIENT: {"name": "张三", "age": 32, "symptoms": []},       # 缺 risk_level + 症状空
    DocKind.LAB: {"patient_name": "张三", "items": []},                 # 无指标
    DocKind.PRESCRIPTION: {"patient_name": "张三", "medications": []},  # 无药品
}


class FakeExtractor:
    """脚本化抽取器：mode 控制失败剧本，离线覆盖流水线所有分支。

    bind(kind) 生成绑定到某类文档的实例，让 pipeline 能直接 extract(prompt)。
    """

    def __init__(self, mode: str = "good", kind: DocKind | None = None) -> None:
        self.mode = mode
        self.kind = kind

    def bind(self, kind: DocKind) -> "FakeExtractor":
        return FakeExtractor(self.mode, kind)

    def extract(self, text: str, kind: DocKind | None = None) -> RawResult:
        kind = kind or self.kind
        if kind is None:
            return RawResult(None, "FakeExtractor: kind 未绑定")
        good = RawResult(json.dumps(_GOOD_BY_KIND[kind], ensure_ascii=False))
        if self.mode == "good":
            return good
        if self.mode == "retry_once":
            # 首次返回语义非法 JSON；prompt 带上"未通过校验"后返回合法 -> 演示自修复
            if "未通过校验" in text:
                return good
            return RawResult(json.dumps(_BAD_BY_KIND[kind], ensure_ascii=False))
        if self.mode == "hopeless":
            # 永远返回坏 JSON -> 演示重试耗尽后的兜底
            return RawResult(json.dumps(_BAD_BY_KIND[kind], ensure_ascii=False))
        return RawResult(None, "抱歉，我只能返回纯文本。")
# [AGC:END]
