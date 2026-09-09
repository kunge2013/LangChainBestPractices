# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""生产观测：按环节分桶计数，定位"谁在拖后腿"。

- record_route      路由来源（rule/model）+ 置信度，低置信度单独计数
- record_validation 校验通过/失败次数
- record_human      人工介入次数
- record_result     最终成功/兜底 + 重试次数
生产里这些数字应接到监控告警（哪个桶高就修哪个），这里保持进程内零依赖。
"""
from typing import Any

from .router import DEFAULT_CONFIDENCE_THRESHOLD

# [AGC:START] tool=Cc author=fangkun
class ProdMetrics:
    """环节分桶指标：success_rate 低时看 route_source / validation_failures 定位。"""

    def __init__(self) -> None:
        self.total = 0
        self.ok = 0
        self.human = 0
        self.fallback = 0
        self.retries_used = 0
        self.route_source: dict[str, int] = {}
        self.low_confidence = 0
        self.validation_failures = 0

    def record_route(self, source: str, confidence: float) -> None:
        self.route_source[source] = self.route_source.get(source, 0) + 1
        if confidence < DEFAULT_CONFIDENCE_THRESHOLD:
            self.low_confidence += 1

    def record_validation(self, *, ok: bool) -> None:
        if not ok:
            self.validation_failures += 1

    def record_human(self) -> None:
        self.human += 1

    def record_result(self, *, ok: bool, attempts_used: int) -> None:
        self.total += 1
        self.retries_used += attempts_used - 1
        if ok:
            self.ok += 1
        else:
            self.fallback += 1

    def summary(self) -> dict[str, Any]:
        rate = round(self.ok / self.total * 100, 2) if self.total else 0.0
        return {
            "total": self.total,
            "ok": self.ok,
            "human_review": self.human,
            "fallback": self.fallback,
            "retries_used": self.retries_used,
            "validation_failures": self.validation_failures,
            "route_source": self.route_source,
            "low_confidence": self.low_confidence,
            "success_rate_%": rate,
        }
# [AGC:END]
