# [AGC:FILE] tool=Cc author=fangkun date=2026-08-24
"""数据模型：状态定义、Bug 模型、测试报告模型。"""
# [AGC:START] tool=Cc author=fangkun
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class BugSeverity(str, Enum):
    """Bug 严重性级别。"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    LOW = "LOW"


class WorkflowStatus(str, Enum):
    """工作流状态。"""

    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass
class BugItem:
    """单个 Bug 条目。"""

    severity: BugSeverity
    description: str
    file: str = ""
    line: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "severity": self.severity.value,
            "description": self.description,
            "file": self.file,
            "line": self.line,
        }


@dataclass
class TestResult:
    """pytest 测试结果。"""

    passed: int = 0
    failed: int = 0
    errors: int = 0
    total: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)
    raw_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "total": self.total,
            "details": self.details,
            "raw_output": self.raw_output,
        }


@dataclass
class LLMReviewResult:
    """LLM 代码审查结果。"""

    bugs: list[BugItem] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "bugs": [bug.to_dict() for bug in self.bugs],
            "summary": self.summary,
        }

    @property
    def critical_count(self) -> int:
        """CRITICAL 级别 bug 数量。"""
        return sum(1 for bug in self.bugs if bug.severity == BugSeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        """HIGH 级别 bug 数量。"""
        return sum(1 for bug in self.bugs if bug.severity == BugSeverity.HIGH)

    @property
    def low_count(self) -> int:
        """LOW 级别 bug 数量。"""
        return sum(1 for bug in self.bugs if bug.severity == BugSeverity.LOW)


@dataclass
class IterationRecord:
    """单轮迭代记录。"""

    round_number: int
    test_result: TestResult
    review_result: LLMReviewResult

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "round_number": self.round_number,
            "test_result": self.test_result.to_dict(),
            "review_result": self.review_result.to_dict(),
            "critical_count": self.review_result.critical_count,
            "high_count": self.review_result.high_count,
            "low_count": self.review_result.low_count,
        }


class AgentState(TypedDict):
    """LangGraph 状态定义。"""

    # 通信
    messages: list[BaseMessage]

    # 输入
    design_doc: str
    requirement: str

    # 工件
    code_artifact: dict[str, str]
    test_results: dict[str, Any]
    bug_list: list[dict[str, Any]]

    # 控制
    iteration_count: int
    max_rounds: int
    status: str

    # 输出
    output_dir: str
    review_dimensions: list[str]

    # 历史
    iteration_history: list[dict[str, Any]]
# [AGC:END]
