# [AGC:FILE] tool=Cc author=fangkun date=2026-07-29
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.utils.uuid import uuid7

load_dotenv()

import os

model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
)


def get_user_info() -> str:
    """Look up information about the current user."""
    return "No user profile on file."


# 短期记忆：PostgreSQL checkpointer 由 langgraph_runtime_postgres 自动管理
# 平台通过 runtime_edition="postgres" 自动注入 PostgreSQL checkpointer
agent = create_agent(
    model=model,
    tools=[get_user_info],
)

# ---------------------------------------------------------------------------
# 测试短期记忆：多轮对话
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 本地测试使用 MemorySaver（不经过平台）
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
    agent = create_agent(
        model=model,
        tools=[get_user_info],
        checkpointer=checkpointer,
    )

    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}

    # 第一轮：告诉 agent 你的名字
    input_1 = {"messages": [HumanMessage(content="我的名字叫小明，请记住。")]}
    print("=== Round 1: 告诉 agent 你的名字 ===")
    for event in agent.stream(input_1, config, stream_mode="messages"):
        msg, _ = event
        if hasattr(msg, "content") and msg.content:
            print(f"  {msg.content[:200]}")

    # 第二轮：问 agent 是否记得你的名字
    input_2 = {"messages": [HumanMessage(content="我叫什么名字？")]}
    print("\n=== Round 2: 问 agent 是否记得你的名字 ===")
    for event in agent.stream(input_2, config, stream_mode="messages"):
        msg, _ = event
        if hasattr(msg, "content") and msg.content:
            print(f"  {msg.content[:200]}")

    print(f"\nThread ID: {thread_id}")
    print("短期记忆验证完成。")