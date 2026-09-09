# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""零依赖观测：JSONL 逐条日志 + 进程内失败率计数器（不需要 LangSmith key 也能常开）。"""
import json
import os
from pathlib import Path
from typing import Any

# [AGC:START] tool=Cc author=fangkun
DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "logs" / "structured_output.jsonl"


class JsonlLogger:
    """以 append 方式写 JSONL，一次调用写一条，避免多进程互相覆盖。"""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.environ.get("STRUCTURED_OUTPUT_LOG", DEFAULT_LOG_PATH))

    def log(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


class FailureCounter:
    """进程内指标：总调用 / 成功 / 最终失败 / 重试次数。"""

    def __init__(self) -> None:
        self.total = 0
        self.ok = 0
        self.failed = 0
        self.retries_used = 0

    def record(self, *, ok: bool, attempts_used: int) -> None:
        self.total += 1
        self.retries_used += attempts_used - 1
        if ok:
            self.ok += 1
        else:
            self.failed += 1

    def summary(self) -> dict[str, Any]:
        rate = (self.ok / self.total * 100.0) if self.total else 0.0
        return {
            "total": self.total,
            "ok": self.ok,
            "failed": self.failed,
            "retries_used": self.retries_used,
            "success_rate_%": round(rate, 2),
        }
# [AGC:END]
