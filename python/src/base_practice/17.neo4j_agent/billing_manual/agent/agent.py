# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual.agent.agent
===========================
Billing manual deep-agent wrapper.

Adapted from 3.billing_manual_agent.py :: BillingAgent.
"""

import logging
from typing import Any

from deepagents import create_deep_agent
from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector
from langchain_openai import ChatOpenAI

from ..config import Config
from ..knowledge.tools import GetSectionImages, KnowledgeSearcher

logger = logging.getLogger(__name__)

# [AGC:START] tool=Cc author=fangkun


class BillingAgent:
    """政企计费账务系统操作助手 — wraps a deep_agent with two retrieval tools."""

    SYSTEM_PROMPT: str = """你是一个政企计费账务系统操作助手，帮助用户理解和完成系统操作。

## 可用工具

1. **search_knowledge** — 根据用户问题关键词检索相关内容（向量相似度匹配）
2. **get_section_images** — 根据章节名称获取该章节全部内容和图片

## 使用策略

- 用户问**具体问题**（如"如何创建新客户"）→ 用 `search_knowledge`
- 用户要**整个章节**（如"给我看客户管理章节的图片"）→ 用 `get_section_images`
- 如果用户提到"章节"、"第X章"、"全部图片" → 优先用 `get_section_images`

## 输出规范

### 操作流程问题
- **文字步骤说明**
- **Mermaid 流程图**：用 ```mermaid 代码块
  ```mermaid
  flowchart TD
      A[步骤1] --> B[步骤2]
      B --> C[步骤3]
  ```
- **相关图片路径**

### 界面/布局问题
- 重点返回图片路径 + 文字描述

### 概念/定义问题
- 直接文字说明，无需流程图

## 图片格式
图片以 HTML img 标签形式返回，如 `<img src="http://localhost:2024/img_0.png" alt="描述" />`。
回答时请直接输出这些 img 标签，让 Markdown 渲染器展示图片。
请用中文回答所有问题。"""

    def __init__(self, config: Config, db: Neo4jVector) -> None:
        self.config = config
        self.db = db
        self.searcher = KnowledgeSearcher(db, config)
        self.section_tool = GetSectionImages(db, config)
        self.agent: Any = None

    def create(self) -> Any:
        """Create and return the deep_agent instance."""
        model = ChatOpenAI(**self.config.get_llm_params())
        self.agent = create_deep_agent(
            model=model,
            tools=[self.searcher, self.section_tool],
            system_prompt=self.SYSTEM_PROMPT,
        )
        return self.agent

    def invoke(self, query: str) -> str:
        """Invoke the agent with a user query and return the response text."""
        if self.agent is None:
            self.create()

        result = self.agent.invoke({"messages": [{"role": "user", "content": query}]})

        if isinstance(result, dict) and "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, "content") and msg.content:
                    return msg.content
        return str(result)

# [AGC:END]
