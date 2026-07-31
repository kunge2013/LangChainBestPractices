# agent tools 调用
from langchain.agents import create_agent
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI



load_dotenv()

import os

model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
)


def get_weather(city) -> str:
    """get weather for give city"""
    return f"{city} 天气"


# 短期记忆：PostgreSQL checkpointer 由 langgraph_runtime_postgres 自动管理
# 平台通过 runtime_edition="postgres" 自动注入 PostgreSQL checkpointer
agent = create_agent(
    model=model,
    tools=[get_weather],
)

print(f'agent = {agent}')
print(f'agent.nodes = {agent.nodes}')
# agent.nodes = {
# '__start__': <langgraph.pregel._read.PregelNode object at 0x000001C9F086CA50>,
# 'model': <langgraph.pregel._read.PregelNode object at 0x000001C9F086C350>,
# 'tools': <langgraph.pregel._read.PregelNode object at 0x000001C9F089B650>}

results = agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "武汉地天气怎样"}
            # {"role": "user", "content": "武汉有多少人"}
        ]
    }
)

msgs = results["messages"]
for msg in msgs:
    msg.pretty_print()
