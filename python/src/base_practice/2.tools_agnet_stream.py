# 流式实现
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

# 1. values -> event 每个完成返回一次 单条消息返回
# for event in agent.stream(
#         {
#             "messages": [
#                 {"role": "user", "content": "武汉地天气怎样"}
#             ]
#         }, stream_mode="values"
# ):
#     messages = event["messages"]
#     print(f"消息长度={len(messages)}")
#     messages[-1].pretty_print()


# 2.messages -> token_by_token 每个完成返回一次  单条消息返回
for chunk in agent.stream(
        {
            "messages": [
                {"role": "user", "content": "武汉地天气怎样"}
            ]
        }, stream_mode="messages"
):
    msg = chunk[0].content
    d = chunk[1]
    print(f"msg = {msg}, d = {d}")

