# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""路由层：把"这是哪类文档"从抽取里独立出来。

- RuleRouter   确定性关键词映射，零成本、零随机、100% 可解释
- ModelRouter  规则判不出时让模型做"选择题"（枚举 + 置信度），低置信度标人工
- Router       组合：规则优先，模棱两可上交模型，置信度低于阈值不赌

设计原则（文档 §12.2/12.3）：能规则就不模型，能选择题就不填空题。
"""
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .schemas import DocKind

# [AGC:START] tool=Cc author=fangkun
# 路由/分流共用的唯一阈值：低置信度不赌，转人工
DEFAULT_CONFIDENCE_THRESHOLD = 0.6


@dataclass
class RouteResult:
    """一次路由的结论。kind=None 表示无法确定（上游应走人工）。"""
    kind: DocKind | None
    confidence: float      # 0~1
    source: str            # "rule" | "model"
    reason: str


class RuleRouter:
    """关键词映射。只对"唯一命中"下判断；模棱两可返回 None 上交模型。"""

    RULES: list[tuple[str, list[str]]] = [
        ("lab_report", ["血常规", "白细胞", "体温", "化验"]),
        ("prescription", ["剂量", "用法", "一日", "毫克", "处方"]),
        ("patient_record", ["症状", "咳嗽", "发烧", "门诊"]),
    ]

    def __init__(self, rules: list[tuple[str, list[str]]] | None = None) -> None:
        self.rules = rules or self.RULES

    def route(self, text: str) -> RouteResult | None:
        hits = [name for name, keywords in self.rules if any(k in text for k in keywords)]
        # 只有唯一命中才下判断；零命中/多命中都交给模型
        if len(hits) == 1:
            return RouteResult(DocKind(hits[0]), 1.0, "rule", f"关键词命中:{hits[0]}")
        return None


class RouteChoice(BaseModel):
    """路由"选择题"的 schema：只要一个答案 + 自评置信度。"""
    model_config = ConfigDict(extra="forbid")

    kind: DocKind
    confidence: int = Field(ge=0, le=100)


class ModelRouter:
    """用 with_structured_output 让模型做选择题；解析 tool_calls[0].args。"""

    def __init__(self, llm: Any, *, method: str = "function_calling") -> None:
        self._runnable = llm.with_structured_output(
            RouteChoice, method=method, include_raw=True
        )

    def route(self, text: str) -> RouteResult:
        try:
            res = self._runnable.invoke(text)
        except Exception as exc:                     # 网络/解析异常也不能让整条请求崩溃
            return RouteResult(None, 0.0, "model", f"路由调用异常: {type(exc).__name__}")
        # 优先用 parsed：它已被 Pydantic 约束（枚举/范围）校验过，无需再手写解析
        parsed = res.get("parsed")
        if isinstance(parsed, RouteChoice):
            return RouteResult(
                parsed.kind, parsed.confidence / 100, "model",
                f"模型置信度{parsed.confidence / 100:.0%}",
            )
        # 兜底解析 raw（含 include_raw=True 的调用）；任何畸形输出都归一化为转人工
        raw = res.get("raw")
        if raw is None:
            return RouteResult(None, 0.0, "model", "路由调用无原始输出")
        try:
            tool_calls = getattr(raw, "tool_calls", None)
            args = (
                tool_calls[0].get("args")
                if tool_calls and isinstance(tool_calls[0], dict)
                else None
            )
            if not isinstance(args, dict):
                return RouteResult(None, 0.0, "model", "路由未返回选择题答案")
            kind_raw, conf_raw = args.get("kind"), args.get("confidence")
            kind = DocKind(kind_raw) if isinstance(kind_raw, str) else None
            conf = (float(conf_raw) if isinstance(conf_raw, (int, float)) else 0.0) / 100
            if kind is None:
                return RouteResult(None, 0.0, "model", "路由未返回合法类型")
            return RouteResult(kind, min(max(conf, 0.0), 1.0), "model", f"模型置信度{conf:.0%}")
        except (ValueError, TypeError):
            return RouteResult(None, 0.0, "model", "路由输出非法，转人工")


class Router:
    """规则优先；规则判不出交给模型选择题；低置信度直接标人工（不赌）。"""

    def __init__(
        self,
        rule_router: RuleRouter | None = None,
        model_router: ModelRouter | None = None,
        *,
        threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.rule_router = rule_router or RuleRouter()
        self.model_router = model_router
        self.threshold = threshold

    def route(self, text: str) -> RouteResult:
        by_rule = self.rule_router.route(text)
        if by_rule is not None:
            return by_rule
        if self.model_router is None:
            return RouteResult(None, 0.0, "none", "无模型路由，且规则无法判定")
        result = self.model_router.route(text)
        # 低置信度不等于"随便猜一个"：改为 kind=None，上游走人工
        if result.kind is not None and result.confidence < self.threshold:
            return RouteResult(None, result.confidence, "model",
                               f"低置信度({result.confidence:.0%})不赌，转人工")
        return result
# [AGC:END]
