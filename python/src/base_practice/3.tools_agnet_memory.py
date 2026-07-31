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


agent = create_agent(
    model=model,
)

print(f'agent = {agent}')
print(f'agent.nodes = {agent.nodes}')
print("============第一轮============")
his_msg = []
# 第一轮问答
results = agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "来一首送词"}
        ]
    },
)

msgs = results["messages"]
his_msg = msgs
for msg in msgs:
    msg.pretty_print()

# 第二轮问答
msg = {"role": "user", "content": "再来一首"}
his_msg.append(msg)
print("============第二轮============")
results = agent.invoke(
    {
        "messages": his_msg
    }
)

msgs = results["messages"]
for msg in msgs:
    msg.pretty_print()
