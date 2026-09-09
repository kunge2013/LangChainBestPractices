# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""生产闭环：路由 -> 抽取 -> 两层校验 -> 重试 -> 人工/兜底。

流程（对应文档 §12.1 流水线图）：
  1. route      规则优先，模棱两可交给模型选择题
  2. 分流       路由定不了 / 低置信度 -> human_review，不赌
  3. 抽取       对选中的单一 schema 抽取（一次只干一件事）
  4. 两层校验   schema 格式层 + 语义业务层
  5. 重试       失败把具体错误喂回 prompt（FIX_TEMPLATE），最多 max_retries 次
  6. 兜底       耗尽给业务 fallback（按 kind），否则标 human_review
"""
import json
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from .extractor import RawResult, SchemaExtractor
from .observability import ProdMetrics
from .router import RouteResult, Router
from .schemas import SCHEMA_BY_KIND, DocKind
from .validate import collect_errors, parse_or_error

# [AGC:START] tool=Cc author=fangkun
FIX_TEMPLATE = (
    "\n\n【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】\n{error}"
)


@dataclass
class ProdAttempt:
    """一次 invoke 的完整轨迹。status: "ok" | "human_review" | "fallback"。"""
    kind: DocKind | None
    route: RouteResult
    status: str
    attempts_used: int
    errors: list[str]
    latency_ms: int


class ProductionPipeline:
    """把『任意文本 -> 某类文档』封装成带人工兜底的生产闭环。"""

    def __init__(
        self,
        router: Router,
        extractors: dict[DocKind, Any],
        *,
        max_retries: int = 2,
        fallbacks: dict[DocKind, BaseModel] | None = None,
        metrics: ProdMetrics | None = None,
    ) -> None:
        self.router = router
        self.extractors = extractors
        self.max_retries = max_retries
        self.fallbacks = fallbacks or {}
        self.metrics = metrics or ProdMetrics()

    def invoke(self, text: str) -> tuple[BaseModel | None, ProdAttempt]:
        started = time.perf_counter()
        route = self.router.route(text)
        self.metrics.record_route(route.source, route.confidence)

        # 路由分流：Router 已把低置信度归一化为 kind=None，这里定不了就走人工，不赌
        if route.kind is None:
            self.metrics.record_human()
            return None, ProdAttempt(
                route.kind, route, "human_review", 0, [route.reason],
                self._ms(started),
            )

        kind, extractor, model_cls = (
            route.kind,
            self.extractors[route.kind],
            SCHEMA_BY_KIND[route.kind],
        )
        errors: list[str] = []
        for attempt in range(1, self.max_retries + 2):
            prompt = text if attempt == 1 else text + FIX_TEMPLATE.format(error=errors[-1])
            raw = extractor.extract(prompt)
            data, parse_errs = parse_or_error(raw.json_str, raw.note)
            if parse_errs:
                self.metrics.record_validation(ok=False)
                errors.extend(parse_errs)
                continue
            errs = collect_errors(kind, model_cls, data)
            if errs:
                self.metrics.record_validation(ok=False)
                errors.extend(errs)
                continue
            obj = model_cls.model_validate(data)          # 兜底一次完整实例化
            self.metrics.record_validation(ok=True)
            self.metrics.record_result(ok=True, attempts_used=attempt)
            return obj, ProdAttempt(kind, route, "ok", attempt, errors, self._ms(started))

        # 重试耗尽：按 kind 的业务 fallback（区别于"ok"）；没有 fallback 就标人工
        self.metrics.record_result(ok=False, attempts_used=self.max_retries + 1)
        fallback = self.fallbacks.get(kind)
        if fallback is None:
            self.metrics.record_human()
            return None, ProdAttempt(
                kind, route, "human_review", self.max_retries + 1,
                errors or ["重试耗尽"], self._ms(started),
            )
        return fallback, ProdAttempt(
            kind, route, "fallback", self.max_retries + 1,
            errors or ["重试耗尽"], self._ms(started),
        )

    @staticmethod
    def _ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
# [AGC:END]
