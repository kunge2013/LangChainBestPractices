### RAG: Retrieval-Augmented Generation
# 检索-增强生成

## 1.理解 RAG
#大模型交互: 问题=>大模型=>回答(生成式)
#基于 RAG 的大模型交互:
# 增强:【问题 +《检索:根据问题找到相似的文本)]=>大模型 =>回答
##从大模型的角度:没有区别，RAG不是大模型技术，是如何更好的用大模型的技术
#RAG 可以看作是一种提示词工程技术
#
##2.扒一下历史，了解RAG的历史地位
# 起源:2020年 Facebook(Meta)论文:《Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
##2018年，Google,基于注意力机制的Transformer架构，改进N/RNN
#2018年,OpenAI,GPT1.e.Generative Pre-Trained Transformer
#2019年，OpenAI.GPT2.0.
#2020年，OpenAI,GPT3.0.对照RAG的起源
#2022年，OpenAI.GPT3.5.chatGPT3.5.

# RAG ， 近几年热度不减，深度应用场景结合

##3.大模型局限: 大模型幻觉
# 1)公开数据，
# 2)时效问题，


## 4.解决方案
# 1)大模型不断实时更新，不可能方案
# 2)微调:用私有数据，新的数据，(标注)局部的训练，垂直行业大模型
# 3)RAG:成本最低，时间短


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


# 短期记忆：PostgreSQL checkpointer 由 langgraph_runtime_postgres 自动管理
# 平台通过 runtime_edition="postgres" 自动注入 PostgreSQL checkpointer
agent = create_agent(
    model=model,
)


results = agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "讲一下3i/Atlas"}
        ]
    }
)

messages = results["messages"]
print(f"历史消息：{len(messages)} 条")
for msg in messages:
    msg.pretty_print()