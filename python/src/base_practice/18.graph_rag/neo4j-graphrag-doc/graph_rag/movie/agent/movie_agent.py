# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
from typing import List, Any
from langchain_core.language_models import BaseLLM
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent


# [AGC:START] tool=Cc author=fangkun
def create_movie_agent(llm: BaseLLM, tools: List[Tool]) -> Any:
    """创建电影问答 Agent（使用 LangGraph ReAct）

    Args:
        llm: 语言模型实例
        tools: 工具列表

    Returns:
        Compiled LangGraph agent
    """
    agent = create_react_agent(
        model=llm,
        tools=tools
    )

    return agent
# [AGC:END]
