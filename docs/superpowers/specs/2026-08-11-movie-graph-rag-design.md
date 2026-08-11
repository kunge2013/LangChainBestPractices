# Movie Graph RAG 系统设计文档

> 日期：2026-08-11
> 作者：fangkun
> 状态：已批准

## 1. 概述

基于 Neo4j 构建电影知识图谱，实现 Graph RAG（Graph Retrieval Augmented Generation）系统。通过 LangChain Agent 编排多种工具，支持结构化查询、语义搜索和智能推荐，以问答形式提供电影信息服务。

## 2. 需求

### 2.1 功能需求

- **结构化查询**：查询电影信息、演员信息、评分等精确问题
- **语义搜索**：基于剧情简介的相似度匹配
- **智能推荐**：结合图结构（共同导演/演员）和语义相似度的混合推荐
- **自然语言问答**：用户可以用自然语言提问，系统生成自然语言回答

### 2.2 非功能需求

- 使用现有 3 部电影的小样本数据，可扩展
- 向量嵌入使用 HuggingFaceEmbeddings（本地模型）
- LLM 使用 ChatOpenAI（OpenAI API）

## 3. 数据模型

### 3.1 节点定义

**Movie（电影）**
- `title` (string, unique) — 电影标题
- `released` (integer) — 上映年份
- `rating` (float) — 评分
- `tagline` (string) — 标语
- `plot_summary` (string) — **新增** 剧情简介，用于向量化
- `genres` (list) — **新增** 电影类型（科幻/悬疑/动作等）
- `keywords` (list) — **新增** 关键词，增强检索质量

**Person（人物）**
- `name` (string, unique) — 姓名
- `born` (integer) — 出生年份
- `gender` (string) — 性别

**Studio（制片厂）**
- `name` (string, unique) — 名称
- `country` (string) — 国家

### 3.2 关系定义

- `Person -ACTED_IN {roles}-> Movie` — 出演
- `Person -DIRECTED-> Movie` — 导演
- `Person -WROTE-> Movie` — 编剧
- `Studio -DISTRIBUTED_BY {year}-> Movie` — 发行

### 3.3 向量索引

对 `plot_summary` 字段建立向量索引，使用 HuggingFaceEmbeddings。

## 4. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    LangChain Agent                          │
│  (ReAct Agent with Tools)                                   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Tool 1       │    │  Tool 2       │    │  Tool 3       │
│  Graph Query  │    │  Vector Search│    │  Recommender  │
│  (Cypher)     │    │  (Semantic)   │    │  (Hybrid)     │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Neo4j Database  │
                    │  ┌─────────────┐  │
                    │  │   Graph     │  │
                    │  │  (Nodes +   │  │
                    │  │   Edges)    │  │
                    │  └─────────────┘  │
                    │  ┌─────────────┐  │
                    │  │   Vector    │  │
                    │  │   Index     │  │
                    │  └─────────────┘  │
                    └───────────────────┘
```

### 4.1 核心组件

**GraphQueryTool（结构化查询工具）**
- 使用 `GraphCypherQAChain` 自动生成 Cypher 查询
- 回答"谁演了 XX"、"XX 的评分"等精确问题
- 支持评分统计、演员列表、导演作品等结构化查询

**VectorSearchTool（语义检索工具）**
- 使用 `Neo4jVector` + HuggingFace embeddings
- 基于 `plot_summary` 做相似度搜索
- 回答"类似 XX 的电影"、"关于太空的电影"等语义问题

**RecommenderTool（混合推荐工具）**
- 结合图结构（共同导演/演员）+ 向量相似度
- 回答"推荐类似 XX 的电影"等复杂推荐问题
- 融合两路结果，去重后排序

## 5. 数据流与问答流程

### 5.1 数据构建流程

```
CSV 数据（扩展现有）
       │
       ▼
┌──────────────────┐
│  数据导入脚本      │
│  ingest_data.py  │
└──────────────────┘
       │
       ├──────────────────────────┐
       ▼                          ▼
┌──────────────┐         ┌──────────────────┐
│ 图数据创建    │         │  向量索引创建      │
│ (MERGE 节点)  │         │  (HuggingFace)    │
│ (MERGE 关系)  │         │  plot_summary     │
└──────────────┘         │  → embedding      │
                          │  → Neo4j Vector   │
                          │    Index          │
                          └──────────────────┘
```

### 5.2 问答流程示例

用户提问："推荐一部类似盗梦空间的烧脑电影"

1. Agent 分析问题类型 → 判定为"推荐类"问题
2. 调用 RecommenderTool
   - 2a. GraphQuery: 查找 Inception 的导演/演员/类型
   - 2b. VectorSearch: 用 Inception 的 plot_summary 做相似度搜索
   - 2c. 融合两路结果，去重
3. ChatOpenAI 生成自然语言回答
   - "推荐《星际穿越》，同为 Christopher Nolan 执导，剧情简介相似度 0.87..."

### 5.3 工具路由逻辑

| 问题类型 | 示例 | 调用工具 |
|---------|------|---------|
| 结构化查询 | "Leonardo DiCaprio 演过哪些电影" | GraphQueryTool |
| 语义搜索 | "关于太空探索的电影简介" | VectorSearchTool |
| 推荐 | "推荐类似 XX 的电影" | RecommenderTool |
| 评分/统计 | "评分最高的电影" | GraphQueryTool |
| 比较 | "比较 Inception 和 Interstellar" | GraphQueryTool + VectorSearchTool |

## 6. 文件结构

```
movie/
├── data_init/                          # 已有
│   ├── __init__.py
│   ├── config.py
│   └── neo4j_utils.py
│
├── config/                             # 新增：配置模块
│   ├── __init__.py
│   └── settings.py                     # LLM、Embedding、Neo4j 配置
│
├── models/                             # 新增：数据模型
│   ├── __init__.py
│   └── movie_data.py                   # 电影数据定义（含 plot_summary）
│
├── ingestion/                          # 新增：数据导入
│   ├── __init__.py
│   ├── ingest_graph.py                 # 图数据导入（节点+关系）
│   └── ingest_vectors.py              # 向量索引构建
│
├── tools/                              # 新增：Agent 工具
│   ├── __init__.py
│   ├── graph_query_tool.py            # 结构化查询工具
│   ├── vector_search_tool.py          # 向量语义检索工具
│   └── recommender_tool.py            # 混合推荐工具
│
├── agent/                              # 新增：Agent 编排
│   ├── __init__.py
│   └── movie_agent.py                  # LangChain ReAct Agent
│
├── main.py                             # 新增：主入口，交互式问答
│
├── chapter_01~11_*.py                  # 已有：教程章节
└── neo4j_tutorial.py                   # 已有：教程主入口
```

### 6.1 组件职责

| 组件 | 职责 | 依赖 |
|------|------|------|
| `config/settings.py` | 统一管理 LLM、Embedding、Neo4j 连接参数 | langchain-openai, sentence-transformers |
| `models/movie_data.py` | 定义扩展电影数据（含 plot_summary、genres） | 无 |
| `ingestion/ingest_graph.py` | 导入节点和关系到 Neo4j | data_init.neo4j_utils |
| `ingestion/ingest_vectors.py` | 对 plot_summary 做 embedding 并建向量索引 | config, HuggingFaceEmbeddings |
| `tools/graph_query_tool.py` | 封装 GraphCypherQAChain 为 LangChain Tool | langchain-neo4j |
| `tools/vector_search_tool.py` | 封装 Neo4jVector retriever 为 Tool | langchain-neo4j, config |
| `tools/recommender_tool.py` | 组合图查询+向量检索的混合推荐 | tools.graph_query_tool, tools.vector_search_tool |
| `agent/movie_agent.py` | 初始化 Agent，注册工具 | langchain agents |
| `main.py` | 交互式命令行问答入口 | agent |

## 7. 错误处理

| 场景 | 处理方式 |
|------|---------|
| Neo4j 连接失败 | 启动时检测，给出明确的连接配置提示 |
| Cypher 生成错误 | 捕获异常，回退到结构化查询模板 |
| 向量检索无结果 | 返回提示信息，建议调整查询关键词 |
| LLM API 超时 | 重试机制（max_retries=3），超时后降级返回原始检索结果 |
| 数据导入冲突 | 使用 MERGE 而非 CREATE，避免重复数据 |

## 8. 测试策略

### 8.1 测试文件结构

```
tests/
├── test_ingestion.py          # 数据导入测试
├── test_tools.py              # 工具功能测试
└── test_agent.py              # Agent 端到端测试
```

### 8.2 测试覆盖

| 测试类型 | 内容 |
|---------|------|
| 单元测试 | 每个 Tool 的输入输出验证 |
| 集成测试 | Neo4j 连接、向量索引创建、数据导入 |
| 端到端测试 | 典型问答场景（结构化查询、语义搜索、推荐） |

### 8.3 测试数据

使用现有 3 部电影的小数据集，测试用例覆盖所有工具类型。

## 9. 技术栈

- **图数据库**：Neo4j 6.x
- **向量嵌入**：HuggingFaceEmbeddings（本地模型）
- **LLM**：ChatOpenAI（OpenAI API）
- **Agent 框架**：LangChain ReAct Agent
- **图查询**：GraphCypherQAChain（自动生成 Cypher）
- **向量检索**：Neo4jVector（内置向量索引）

## 10. 实施计划

1. **阶段一**：数据模型扩展与导入
   - 扩展电影数据（添加 plot_summary、genres）
   - 实现数据导入脚本

2. **阶段二**：工具开发
   - 实现 GraphQueryTool
   - 实现 VectorSearchTool
   - 实现 RecommenderTool

3. **阶段三**：Agent 集成
   - 实现 LangChain Agent
   - 注册工具
   - 实现交互式问答界面

4. **阶段四**：测试与优化
   - 编写单元测试和集成测试
   - 端到端测试验证
   - 性能优化
