# [AGC:FILE] tool=Cc author=fangkun date=2026-08-24
"""Agent 定义：开发者和测试者。"""
# [AGC:START] tool=Cc author=fangkun
from __future__ import annotations

import sys
from pathlib import Path

# 添加当前目录到 Python 路径
_current_dir = Path(__file__).parent.resolve()
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import Config
from tools import edit_file, read_file, run_command, write_file


def create_developer_agent(config: Config) -> Any:
    """创建开发者 Agent。

    负责根据设计文档生成代码。
    """
    tools = [read_file, write_file, edit_file, run_command]

    llm_kwargs = {
        "model": config.developer_model,
        "temperature": 0.3,
    }
    if config.base_url:
        llm_kwargs["base_url"] = config.base_url
    if config.api_key:
        llm_kwargs["api_key"] = config.api_key

    llm = ChatOpenAI(**llm_kwargs)

    agent = create_react_agent(
        model=llm,
        tools=tools,
    )

    return agent


def create_tester_agent(config: Config) -> Any:
    """创建测试者 Agent。

    负责生成测试、运行测试、进行代码审查。
    """
    tools = [run_command]

    llm_kwargs = {
        "model": config.tester_model,
        "temperature": 0.1,
    }
    if config.base_url:
        llm_kwargs["base_url"] = config.base_url
    if config.api_key:
        llm_kwargs["api_key"] = config.api_key

    llm = ChatOpenAI(**llm_kwargs)

    agent = create_react_agent(
        model=llm,
        tools=tools,
    )

    return agent

# [AGC:END]
