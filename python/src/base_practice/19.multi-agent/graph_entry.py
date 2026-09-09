# [AGC:FILE] tool=Cc author=fangkun date=2026-08-24
"""LangGraph 独立入口：供 langgraph.json 配置使用。

这个模块提供了一个独立的入口点，可以在 langgraph.json 中配置使用。
它导出一个编译好的 LangGraph 状态图对象。
"""
# [AGC:START] tool=Cc author=fangkun
from __future__ import annotations

import sys
from pathlib import Path

# 添加当前目录到 Python 路径，以便导入同目录的模块
_current_dir = Path(__file__).parent.resolve()
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

# 添加 python 目录到路径
_python_dir = _current_dir.parent.parent.parent.parent
if str(_python_dir) not in sys.path:
    sys.path.insert(0, str(_python_dir))

import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 现在可以导入同目录的模块
from config import Config
from graph import build_graph
from models import AgentState, WorkflowStatus


def create_workflow(
    design_doc: str = "",
    requirement: str = "",
    output_dir: str | None = None,
) -> Any:
    """创建工作流实例。

    Args:
        design_doc: 设计文档内容
        requirement: 用户补充需求
        output_dir: 输出目录

    Returns:
        编译后的 LangGraph 工作流
    """
    config = Config()

    if output_dir:
        config.output_dir = output_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config.output_dir = f"./output/multi_agent_{timestamp}"

    # 创建工作目录
    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(config.workspace_dir, exist_ok=True)

    # 构建状态图
    graph = build_graph(config)

    return graph


# 全局配置实例
_config = Config()

# 确保工作目录存在
os.makedirs(_config.output_dir, exist_ok=True)
os.makedirs(_config.workspace_dir, exist_ok=True)

# 导出供 langgraph.json 使用的 graph 对象
graph = build_graph(_config)

# [AGC:END]
