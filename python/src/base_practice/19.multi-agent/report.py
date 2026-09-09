# [AGC:FILE] tool=Cc author=fangkun date=2026-08-24
"""报告生成器：Markdown + JSON 双格式输出，以及代码逻辑文档生成。"""
# [AGC:START] tool=Cc author=fangkun
from __future__ import annotations

import sys
from pathlib import Path

# 添加当前目录到 Python 路径
_current_dir = Path(__file__).parent.resolve()
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

import json
import os
from datetime import datetime
from typing import Any

from models import (
    BugItem,
    BugSeverity,
    IterationRecord,
    LLMReviewResult,
    TestResult,
    WorkflowStatus,
)


def generate_test_report(
    status: WorkflowStatus,
    iteration_history: list[IterationRecord],
    output_dir: str,
) -> None:
    """生成测试报告（Markdown + JSON）。

    Args:
        status: 工作流最终状态
        iteration_history: 所有迭代记录
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)

    # 生成 Markdown 报告
    md_path = os.path.join(output_dir, "test_report.md")
    _write_markdown_report(md_path, status, iteration_history)

    # 生成 JSON 报告
    json_path = os.path.join(output_dir, "test_report.json")
    _write_json_report(json_path, status, iteration_history)


def _write_markdown_report(
    path: str,
    status: WorkflowStatus,
    history: list[IterationRecord],
) -> None:
    """写入 Markdown 测试报告。"""
    total_rounds = len(history)
    final_round = history[-1] if history else None

    final_critical = final_round.review_result.critical_count if final_round else 0
    final_high = final_round.review_result.high_count if final_round else 0
    final_low = final_round.review_result.low_count if final_round else 0

    lines = [
        "# 测试报告\n",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "\n## 概览\n",
        f"- **状态**: {status.value}",
        f"- **迭代轮数**: {total_rounds}",
        f"- **最终 CRITICAL bug**: {final_critical}",
        f"- **最终 HIGH bug**: {final_high}",
        f"- **最终 LOW bug**: {final_low}",
        "",
        "\n## Bug 列表\n",
    ]

    if final_round:
        bugs = final_round.review_result.bugs
        for severity in [BugSeverity.CRITICAL, BugSeverity.HIGH, BugSeverity.LOW]:
            severity_bugs = [b for b in bugs if b.severity == severity]
            lines.append(f"### {severity.value}\n")
            if severity_bugs:
                for i, bug in enumerate(severity_bugs, 1):
                    loc = f" ({bug.file}:{bug.line})" if bug.file else ""
                    lines.append(f"{i}. [{severity.value}] {bug.description}{loc}")
            else:
                lines.append("（无）")
            lines.append("")
    else:
        lines.append("（无迭代记录）\n")

    lines.append("\n## 测试结果\n")
    if final_round:
        tr = final_round.test_result
        lines.extend([
            f"- **通过**: {tr.passed}",
            f"- **失败**: {tr.failed}",
            f"- **错误**: {tr.errors}",
            f"- **总计**: {tr.total}",
            "",
        ])
        if tr.details:
            lines.append("| 测试用例 | 状态 | 耗时 |")
            lines.append("|----------|------|------|")
            for d in tr.details:
                status_icon = "PASS" if d.get("passed", False) else "FAIL"
                lines.append(
                    f"| {d.get('name', 'unknown')} | {status_icon} | {d.get('duration', 'N/A')} |"
                )
            lines.append("")
    else:
        lines.append("（无测试记录）\n")

    lines.append("\n## 迭代历史\n")
    for record in history:
        rr = record.review_result
        lines.append(
            f"- **Round {record.round_number}**: "
            f"{rr.critical_count} CRITICAL, {rr.high_count} HIGH, {rr.low_count} LOW"
        )
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_json_report(
    path: str,
    status: WorkflowStatus,
    history: list[IterationRecord],
) -> None:
    """写入 JSON 测试报告。"""
    final_round = history[-1] if history else None
    final_test = final_round.test_result if final_round else TestResult()

    data = {
        "status": status.value,
        "generated_at": datetime.now().isoformat(),
        "total_rounds": len(history),
        "iterations": [record.to_dict() for record in history],
        "test_summary": {
            "passed": final_test.passed,
            "failed": final_test.failed,
            "errors": final_test.errors,
            "total": final_test.total,
        },
        "final_bugs": (
            [b.to_dict() for b in final_round.review_result.bugs]
            if final_round else []
        ),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_code_logic_doc(
    code_artifact: dict[str, str],
    output_dir: str,
) -> None:
    """生成代码逻辑文档（模块概览 + 函数级文档）。

    Args:
        code_artifact: {文件路径: 文件内容}
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    doc_path = os.path.join(output_dir, "code_logic.md")

    lines = [
        "# 代码逻辑文档\n",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "\n## 模块概览\n",
        f"共 {len(code_artifact)} 个文件：\n",
    ]

    for filepath in sorted(code_artifact.keys()):
        lines.append(f"- `{filepath}`")
    lines.append("")

    for filepath in sorted(code_artifact.keys()):
        content = code_artifact[filepath]
        lines.extend([
            f"\n## 文件: `{filepath}`\n",
            f"代码行数: {len(content.splitlines())}",
            "",
        ])

        # 提取函数和类信息
        functions = _extract_functions(content)
        classes = _extract_classes(content)

        if classes:
            lines.append("### 类\n")
            for cls in classes:
                lines.append(f"#### `class {cls['name']}`\n")
                if cls.get("bases"):
                    lines.append(f"继承: {', '.join(cls['bases'])}\n")
                if cls.get("docstring"):
                    lines.append(f"{cls['docstring']}\n")
                lines.append("")

        if functions:
            lines.append("### 函数\n")
            for func in functions:
                lines.append(f"#### `{func['signature']}`\n")
                if func.get("docstring"):
                    lines.append(f"{func['docstring']}\n")
                lines.append("")

        if not classes and not functions:
            lines.append("（无类或函数定义）\n")

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _extract_functions(code: str) -> list[dict[str, Any]]:
    """从代码中提取函数信息。"""
    functions = []
    lines = code.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("def ") or line.startswith("async def "):
            # 提取签名（可能跨行）
            sig_lines = [lines[i].strip()]
            while ")" not in sig_lines[-1] and i + 1 < len(lines):
                i += 1
                sig_lines.append(lines[i].strip())
            signature = " ".join(sig_lines)
            # 清理装饰器残留
            signature = signature.lstrip("async ").strip()

            # 提取 docstring
            docstring = ""
            j = i + 1
            if j < len(lines):
                next_line = lines[j].strip()
                if next_line.startswith('"""') or next_line.startswith("'''"):
                    quote = next_line[:3]
                    if next_line.count(quote) >= 2 and len(next_line) > 3:
                        docstring = next_line[3:-3].strip()
                    else:
                        doc_parts = [next_line[3:]]
                        j += 1
                        while j < len(lines):
                            if quote in lines[j]:
                                doc_parts.append(lines[j].strip()[:-3])
                                break
                            doc_parts.append(lines[j].strip())
                            j += 1
                        docstring = " ".join(doc_parts).strip()

            func_name = line.split("def ")[-1].split("(")[0] if "def " in line else ""
            functions.append({
                "name": func_name,
                "signature": signature,
                "docstring": docstring,
            })
        i += 1

    return functions


def _extract_classes(code: str) -> list[dict[str, Any]]:
    """从代码中提取类信息。"""
    classes = []
    lines = code.splitlines()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("class "):
            # 解析类名和基类
            header = stripped.split(":", 1)[0]
            parts = header.split("class ", 1)[-1]
            if "(" in parts:
                name = parts.split("(")[0].strip()
                bases_str = parts.split("(", 1)[-1].rstrip(")")
                bases = [b.strip() for b in bases_str.split(",") if b.strip()]
            else:
                name = parts.strip()
                bases = []

            # 提取 docstring
            docstring = ""
            j = i + 1
            if j < len(lines):
                next_line = lines[j].strip()
                if next_line.startswith('"""') or next_line.startswith("'''"):
                    quote = next_line[:3]
                    if next_line.count(quote) >= 2 and len(next_line) > 3:
                        docstring = next_line[3:-3].strip()

            classes.append({
                "name": name,
                "bases": bases,
                "docstring": docstring,
            })

    return classes
# [AGC:END]
