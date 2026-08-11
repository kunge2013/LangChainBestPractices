# Movie Graph RAG

基于 Neo4j 的电影知识图谱 Graph RAG 系统。

## 功能

- **结构化查询**：查询电影信息、演员信息、评分等
- **语义搜索**：基于剧情简介的相似度匹配
- **智能推荐**：结合图结构和语义相似度的混合推荐

## 安装

```bash
pip install langchain langchain-openai langchain-neo4j sentence-transformers neo4j langgraph
```

## 使用

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并配置 Neo4j 连接信息。

### 2. 准备数据

```bash
python movie/prepare_data.py
```

### 3. 启动问答系统

```bash
python movie/main.py
```

### 4. 提问示例

- "Leonardo DiCaprio 演过哪些电影？"
- "Inception 的评分是多少？"
- "推荐一部类似盗梦空间的电影"
- "关于太空探索的电影有哪些？"

## 架构

- **LangChain Agent**：ReAct 模式编排工具
- **GraphQueryTool**：GraphCypherQAChain 自动生成 Cypher
- **VectorSearchTool**：Neo4jVector + HuggingFaceEmbeddings
- **RecommenderTool**：混合图查询和向量检索

## 技术栈

- Neo4j 6.x
- LangChain
- HuggingFaceEmbeddings
- ChatOpenAI
