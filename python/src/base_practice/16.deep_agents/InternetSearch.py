# agent tools 调用
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent

load_dotenv()

import os

model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
)

# 定义网络搜索工具
def internet_search(query: str, max_results: int = 5, topic: str = "general", include_raw_content: bool = False):
    """
    执行网络搜索

    Args:
        query: 搜索查询字符串
        max_results: 返回的最大结果数
        topic: 搜索主题 (general, news, etc.)
        include_raw_content: 是否包含原始内容
    """
    # 示例：使用DuckDuckGo API
    try:
        import requests
        import json

        # DuckDuckGo Instant Answer API
        search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
        response = requests.get(search_url, timeout=10)
        data = response.json()

        # 处理返回结果
        formatted_results = []

        # 添加摘要信息
        if data.get('Abstract'):
            formatted_results.append({
                'title': 'Summary',
                'url': data.get('AbstractURL', ''),
                'snippet': data.get('Abstract', '')
            })

        # 添加相关主题
        for result in data.get('RelatedTopics', [])[:max_results]:
            if 'Text' in result and 'FirstURL' in result:
                formatted_results.append({
                    'title': result.get('Text', '')[:100],
                    'url': result.get('FirstURL', ''),
                    'snippet': result.get('Text', '')
                })

        # 如果没有结果，返回基本信息
        if not formatted_results:
            formatted_results.append({
                'title': f'关于 "{query}" 的搜索结果',
                'url': f'https://duckduckgo.com/?q={query}',
                'snippet': f'请在浏览器中查看 "{query}" 的详细搜索结果'
            })

        return formatted_results

    except Exception as e:
        return [{
            'title': '搜索错误',
            'url': '',
            'snippet': f'搜索时发生错误: {str(e)}'
        }]

# 系统提示
research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

You have access to an internet search tool as your primary means of gathering information.

## `internet_search`

Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.

When you search, make sure to:
1. Use specific, targeted queries
2. Synthesize information from multiple sources
3. Verify facts when possible
4. Cite your sources

IMPORTANT: Always respond in Chinese (中文) when the user asks in Chinese.
"""

# 创建代理
agent = create_deep_agent(
    model=model,
    tools=[internet_search],
    system_prompt=research_instructions,
)

# 调用代理
result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "武汉在那个省？检索一下，请详细回答并说明你的信息来源。"
    }]
})

if 'messages' in result:
    for i, msg in enumerate(result['messages']):
        msg.pretty_print()