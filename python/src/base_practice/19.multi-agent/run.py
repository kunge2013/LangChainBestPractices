# [AGC:FILE] tool=Cc author=fangkun date=2026-08-24
"""CLI 入口：运行开发-测试协同工作流。"""
# [AGC:START] tool=Cc author=fangkun
from __future__ import annotations

import sys
from pathlib import Path

# 添加当前目录到 Python 路径
_current_dir = Path(__file__).parent.resolve()
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

import argparse
import os

from dotenv import load_dotenv

# 加载环境变量配置
load_dotenv(override=True)

from config import Config
from graph import build_graph
from models import (
    BugItem,
    BugSeverity,
    IterationRecord,
    LLMReviewResult,
    TestResult,
    WorkflowStatus,
)
from report import generate_code_logic_doc, generate_test_report


def run_workflow(
    design_doc_path: str,
    requirement: str = "",
    config: Config | None = None,
) -> dict:
    """运行开发-测试协同工作流。

    Args:
        design_doc_path: 设计文档路径
        requirement: 用户补充需求
        config: 配置对象，为 None 时使用默认配置

    Returns:
        最终状态字典
    """
    if config is None:
        config = Config()

    # 读取设计文档
    with open(design_doc_path, "r", encoding="utf-8") as f:
        design_content = f.read()

    # 创建输出目录
    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(config.workspace_dir, exist_ok=True)

    # 设置环境变量供工具使用
    os.environ["WORKSPACE_DIR"] = config.workspace_dir

    # 构建状态图
    app = build_graph(config)

    # 初始化状态
    initial_state = {
        "messages": [],
        "design_doc": design_content,
        "requirement": requirement,
        "code_artifact": {},
        "test_results": {},
        "bug_list": [],
        "iteration_count": 0,
        "max_rounds": config.max_rounds,
        "status": WorkflowStatus.IN_PROGRESS.value,
        "output_dir": config.output_dir,
        "review_dimensions": config.review_dimensions,
        "iteration_history": [],
    }

    # 运行工作流
    final_state = app.invoke(initial_state)

    # 生成报告
    _generate_outputs(final_state, config)

    return final_state


def _generate_outputs(final_state: dict, config: Config) -> None:
    """生成最终输出文件。"""

    status_str = final_state.get("status", WorkflowStatus.FAILED.value)
    try:
        status = WorkflowStatus(status_str)
    except ValueError:
        status = WorkflowStatus.FAILED

    # 解析迭代历史
    history = []
    for record_dict in final_state.get("iteration_history", []):
        tr_dict = record_dict.get("test_result", {})
        test_result = TestResult(
            passed=tr_dict.get("passed", 0),
            failed=tr_dict.get("failed", 0),
            errors=tr_dict.get("errors", 0),
            total=tr_dict.get("total", 0),
            details=tr_dict.get("details", []),
            raw_output=tr_dict.get("raw_output", ""),
        )

        rr_dict = record_dict.get("review_result", {})
        bugs = []
        for b in rr_dict.get("bugs", []):
            try:
                severity = BugSeverity(b.get("severity", "LOW"))
            except ValueError:
                severity = BugSeverity.LOW
            bugs.append(BugItem(
                severity=severity,
                description=b.get("description", ""),
                file=b.get("file", ""),
                line=b.get("line", 0),
            ))
        review_result = LLMReviewResult(
            bugs=bugs,
            summary=rr_dict.get("summary", ""),
        )

        history.append(IterationRecord(
            round_number=record_dict.get("round_number", 0),
            test_result=test_result,
            review_result=review_result,
        ))

    # 生成测试报告（Markdown + JSON）
    generate_test_report(status, history, config.output_dir)

    # 仅在 PASSED 时生成代码逻辑文档
    if status == WorkflowStatus.PASSED:
        generate_code_logic_doc(
            final_state.get("code_artifact", {}),
            config.output_dir,
        )


def main() -> None:
    """CLI 主入口。"""
    parser = argparse.ArgumentParser(
        description="多 Agent 协同开发模块：开发-测试-修复循环",
    )
    parser.add_argument(
        "--design",
        required=True,
        help="设计文档路径（Markdown 文件）",
    )
    parser.add_argument(
        "--requirement",
        default="",
        help="用户补充需求描述",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出根目录（默认: ./output/{timestamp}）",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="最大迭代轮数（默认: 5）",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM 模型名称（默认: gpt-4o）",
    )
    parser.add_argument(
        "--review-dimensions",
        default=None,
        help="审查维度，逗号分隔（默认: correctness,quality,edge_cases）",
    )

    args = parser.parse_args()

    # 验证设计文档存在
    if not os.path.exists(args.design):
        print(f"错误: 设计文档不存在: {args.design}", file=sys.stderr)
        sys.exit(1)

    # 构建配置
    config_dict = {}
    if args.output:
        config_dict["output_dir"] = args.output
    if args.max_rounds:
        config_dict["max_rounds"] = args.max_rounds
    if args.model:
        config_dict["developer_model"] = args.model
        config_dict["tester_model"] = args.model
    if args.review_dimensions:
        config_dict["review_dimensions"] = [
            d.strip() for d in args.review_dimensions.split(",")
        ]

    config = Config.from_dict(config_dict)

    print(f"[START] workflow started")
    print(f"   design doc: {args.design}")
    print(f"   requirement: {args.requirement or '(none)'}")
    print(f"   output dir: {config.output_dir}")
    print(f"   max rounds: {config.max_rounds}")
    print(f"   review dims: {', '.join(config.review_dimensions)}")
    print()

    # 运行工作流
    final_state = run_workflow(args.design, args.requirement, config)

    # 输出结果摘要
    status = final_state.get("status", "UNKNOWN")
    iterations = final_state.get("iteration_count", 0)

    print()
    print("=" * 60)
    print(f"[DONE] workflow finished")
    print(f"   status: {status}")
    print(f"   iterations: {iterations}")
    print(f"   output dir: {config.output_dir}")
    print()
    print("生成的文件:")
    for root, dirs, files in os.walk(config.output_dir):
        level = root.replace(config.output_dir, "").count(os.sep)
        indent = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = "  " * (level + 1)
        for f in files:
            print(f"{sub_indent}{f}")


if __name__ == "__main__":
    main()
# [AGC:END]
