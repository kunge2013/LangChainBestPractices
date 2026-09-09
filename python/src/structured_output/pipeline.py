# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""最小可靠闭环：生成 -> 语法解析 -> Pydantic 严格校验 -> 带错误反馈重试 -> 兜底 + 观测。

保证层次：
  1. 语法层：with_structured_output / JSON mode 让模型尽量输出合法 JSON
  2. schema 层：json.loads + Pydantic 严格校验（字段齐全、类型正确、枚举合法）
  3. 修复层：校验失败时把错误喂回 prompt 让模型自纠正，可配置次数
  4. 兜底层：重试耗尽后返回 None + 结构化日志 + 失败计数（fallback 可配置）
"""
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from .extractors import RawResult
from .observability import FailureCounter, JsonlLogger

# [AGC:START] tool=Cc author=fangkun
FIX_TEMPLATE = (
    "\n\n【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】\n{error}"
)


@dataclass
class Attempt:
    """单次调用的完整轨迹，供上层业务与观测层使用。"""
    request_id: str
    status: str                       # "ok" | "fallback"
    attempts_used: int                # 1 + 重试次数
    errors: list[str] = field(default_factory=list)
    latency_ms: int = 0


class StructuredOutputPipeline:
    """把任意『文本 -> JSON 字符串』抽取器包装成带保证的闭环。"""

    def __init__(
        self,
        extractor: Any,
        schema: type[BaseModel],
        *,
        max_retries: int = 2,
        fallback: BaseModel | None = None,
        logger: JsonlLogger | None = None,
        counter: FailureCounter | None = None,
        provider: str = "unknown",
        model: str = "unknown",
        method: str = "unknown",
    ) -> None:
        self.extractor = extractor
        self.schema = schema
        self.max_retries = max_retries
        self.fallback = fallback               # 兜底实例；默认 None
        self.logger = logger or JsonlLogger()
        self.counter = counter or FailureCounter()
        self._meta = {"provider": provider, "model": model, "method": method}

    def invoke(self, text: str) -> tuple[BaseModel | None, Attempt]:
        request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        errors: list[str] = []
        last_prompt, last_raw = text, RawResult(None, "")

        for attempt in range(1, self.max_retries + 2):
            prompt = text if attempt == 1 else text + FIX_TEMPLATE.format(error=errors[-1])
            last_prompt, last_raw = prompt, self.extractor.extract(prompt)
            try:
                obj = self._validate(last_raw)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                self._emit(request_id, attempt, "retry", errors[-1], last_prompt, last_raw, None)
                continue
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.counter.record(ok=True, attempts_used=attempt)
            self._emit(request_id, attempt, "ok", "", last_prompt, last_raw, obj.model_dump())
            return obj, Attempt(request_id, "ok", attempt, errors, latency_ms)

        latency_ms = int((time.perf_counter() - started) * 1000)
        self.counter.record(ok=False, attempts_used=self.max_retries + 1)
        last = errors[-1] if errors else "重试耗尽"
        self._emit(request_id, self.max_retries + 1, "fallback", last, last_prompt, last_raw, None)
        return self.fallback, Attempt(request_id, "fallback", self.max_retries + 1, errors, latency_ms)

    def _validate(self, raw: RawResult) -> BaseModel:
        """语法层 + schema 层：缺 JSON / JSON 解析失败 / Pydantic 严格校验失败都抛错。"""
        if not raw.json_str:
            raise ValueError(raw.note or "模型未返回可解析的 JSON")
        data: Any = json.loads(raw.json_str)                       # 语法层
        return self.schema.model_validate(data)                    # schema 层（strict 由 Field/Config 控制）

    def _emit(
        self,
        request_id: str,
        attempt: int,
        status: str,
        error: str,
        prompt: str,
        raw: RawResult,
        parsed: dict | None,
    ) -> None:
        """记录完整调用轨迹：完整 prompt、原始响应结构、解析结果。"""
        self.logger.log(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "request_id": request_id,
                "status": status,
                "attempt": attempt,
                "max_retries": self.max_retries,
                "error": error[:400],
                "prompt": prompt,
                "raw_json": raw.json_str,
                "raw_message": raw.raw_message,
                "parsed": parsed,
                **self._meta,
            }
        )
# [AGC:END]
