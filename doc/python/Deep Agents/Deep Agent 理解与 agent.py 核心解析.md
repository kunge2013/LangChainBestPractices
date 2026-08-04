# Deep Agent 理解与 agent.py 核心解析

> 生成日期: 2026-07-29
> 分析对象: `python/src/data_analysis/agent.py` + `python/src/data_analysis/data_analysis_agent.py`
> 参考文档: LangChain Deep Agents 官方文档

---

## 一、对 Deep Agent 的理解

### 1.1 什么是 Deep Agent

Deep Agent 是 LangChain 框架中的一种**深度智能体（Deep Agent）**，它不仅仅是一个简单的 "LLM + tools" 组合，而是一个完整的**自主推理与执行系统**。核心特征：

- **规划能力**：能自主拆解任务、维护 TODO list、决定执行顺序
- **代码执行**：通过 Backend（沙箱或本地 shell）运行代码、读写文件
- **工具扩展**：支持自定义工具（如 Slack 发送消息）与内置工具（文件系统、shell、子代理）
- **上下文管理**：内置上下文压缩（offloading + summarization），防止上下文窗口溢出
- **持久化记忆**：通过 checkpointer 支持多轮对话和跨会话记忆

### 1.2 Deep Agent 的核心组件架构

```
+---------------------------------------------------+
|                    Deep Agent                      |
|                                                    |
|  +-------------+    +-------------+  +-----------+ |
|  |    LLM      |    |   Tools     |  |  Backend  | |
|  |  (Model)    |<-->| (Custom +   |<->| (Sandbox  | |
|  |             |    |  Built-in)  |  |  /Local)  | |
|  +-------------+    +-------------+  +-----------+ |
|        ^                   ^               ^       |
|        |                   |               |       |
|  +-----+-----+    +--------+-------+ +-----+-----+ |
|  | System    |    | Checkpointer   | | Context   | |
|  | Prompt    |    | (Memory)       | | Compression| |
|  +-----------+    +----------------+ +-----------+ |
+---------------------------------------------------+
```

### 1.3 上下文工程（Context Engineering）

Deep Agent 通过 5 种上下文类型来管理信息流：

| 类型 | 作用域 | 用途 |
|------|--------|------|
| **Input Context** | 每次启动 | System prompt、Memory（AGENTS.md）、Skills |
| **Runtime Context** | 每次调用 | 用户元数据、API keys、配置 |
| **Context Compression** | 自动触发 | Offloading（>20K tokens 存文件）+ Summarization（85% 窗口阈值） |
| **Context Isolation** | 子代理 | 通过 subagent 隔离重型工作，只返回结果 |
| **Long-term Memory** | 跨会话 | 通过 `/memories/` 路径 + LangGraph Store 持久化 |

#### 上下文压缩机制

1. **Offloading（卸载）**：当工具调用输入或结果超过 20,000 tokens 时，自动将内容写入文件系统，在对话历史中替换为文件引用
2. **Summarization（摘要）**：当上下文达到模型窗口的 85% 时，LLM 自动生成对话摘要，保留最近 10% 的原始消息

### 1.4 Backend 系统

Backend 是 Deep Agent 执行代码的环境，支持多种提供者：

| Backend | 适用场景 | 特点 |
|---------|----------|------|
| **LocalShellBackend** | 开发/测试 | 本地 shell 执行，`virtual_mode=True` 时模拟沙箱 |
| **LangSmithSandbox** | 生产 | LangSmith 提供的云沙箱 |
| **Daytona** | 生产 | 第三方沙箱服务 |
| **E2B** | 生产 | 第三方沙箱服务 |
| **Modal** | 生产 | Serverless 容器沙箱 |
| **Runloop** | 生产 | 开发环境沙箱 |
| **AgentCoreSandbox** | 生产 | AWS Bedrock 代码解释器 |

### 1.5 系统 Prompt 组装顺序

Deep Agent 的最终系统 prompt 由以下部分按顺序拼接而成：

1. 自定义 `system_prompt`（如果提供）
2. Base agent prompt（内置基础提示）
3. To-do list prompt（规划指令）
4. Memory prompt（AGENTS.md 内容，如果有）
5. Skills prompt（Skills 内容，如果有）
6. Virtual filesystem prompt（文件系统工具文档）
7. Subagent prompt（子代理使用指南）
8. 用户自定义 middleware prompts
9. Human-in-the-loop prompt（如果设置了 `interrupt_on`）

### 1.6 Agent 执行流程

```
用户请求
    |
    v
+---------------------------+
|  LangGraph Dev Server     |  (app.py 启动)
|  加载 langgraph.json      |
+------------+--------------+
             |
             v
+---------------------------+
|  导入 agent.py:agent      |  <-- 模块级副作用：创建数据、上传文件
+------------+--------------+
             |
             v
+---------------------------+
|  Deep Agent 接收请求      |
|  1. 解析用户意图          |
|  2. 规划执行步骤          |
|  3. 使用工具链            |
|     - read_file           |
|     - write_file          |
|     - execute             |
|     - slack_send_message  |
|  4. 通过 Backend 执行代码 |
+------------+--------------+
             |
             v
+---------------------------+
|  Backend (LocalShell)     |
|  - 读写 /root/data/       |
|  - 执行 python 脚本       |
|  - 生成 plots + reports   |
+------------+--------------+
             |
             v
       返回结果 / 发送 Slack
```

---

## 二、agent.py 核心解析

### 2.1 文件角色

`agent.py`（`src/data_analysis/agent.py`）是这个项目的**核心 Graph 定义文件**。它在 `langgraph.json` 中被注册为：

```json
{
  "graphs": {
    "data_analysis": "./src/data_analysis/agent.py:agent"
  }
}
```

这意味着当 LangGraph dev server 启动时，会从该文件导入 `agent` 对象作为 `data_analysis` graph 的入口。

### 2.2 核心组件逐层拆解

#### 层 1：Backend 设置（第 18-23 行）

```python
backend = LocalShellBackend(
    root_dir=".",
    virtual_mode=True,
    env={"PATH": "/usr/bin:/bin"},
)
```

| 参数 | 值 | 含义 |
|------|-----|------|
| `root_dir` | `"."` | 根目录为当前工作目录 |
| `virtual_mode` | `True` | 启用虚拟模式，在 `/root` 路径下模拟隔离的文件系统 |
| `env` | `{"PATH": "/usr/bin:/bin"}` | 限制子进程的环境变量，缩小 PATH 范围 |

**这个 backend 负责**：
- 文件读写（`upload_files` / `download_files`）
- Shell 命令执行（`execute` 工具）
- 代码脚本的运行（如 `python analyze_sales.py`）

#### 层 2：数据准备（第 27-43 行）

```python
data = [
    ["Date", "Product", "Units Sold", "Revenue"],
    ["2025-08-01", "Widget A", 10, 250],
    ...
]
text_buf = io.StringIO()
writer = csv.writer(text_buf)
writer.writerows(data)
csv_bytes = text_buf.getvalue().encode("utf-8")
text_buf.close()

backend.upload_files([("/root/data/sales_data.csv", csv_bytes)])
```

**重要**：这段代码在模块加载时就创建并上传了示例 CSV 数据。这意味着每次导入 `agent.py` 时都会执行——这是一个**模块级副作用**。

**潜在问题**：
- 当 `langgraph dev --reload` 触发热重载时，每次代码变动都会重新上传数据
- 如果用户已经在沙箱里修改了 `sales_data.csv`，重载后修改会被覆盖
- 在生产部署中，这个副作用会在每次 worker 启动时执行

#### 层 3：自定义工具（第 47-77 行）

```python
tools = []

slack_token = os.environ.get("SLACK_USER_TOKEN")
if slack_token:
    from slack_sdk import WebClient

    slack_client = WebClient(token=slack_token)
    slack_channel = os.environ.get("SLACK_CHANNEL", "C0123456ABC")

    @tool(parse_docstring=True)
    def slack_send_message(text: str, file_path: str | None = None) -> str:
        """Send message, optionally including attachments such as images."""
        if not file_path:
            slack_client.chat_postMessage(channel=slack_channel, text=text)
        else:
            fp = backend.download_files([file_path])
            slack_client.files_upload_v2(
                channel=slack_channel,
                content=fp[0].content,
                initial_comment=text,
            )
        return "Message sent."

    tools.append(slack_send_message)
```

**设计要点**：
- 条件性地添加 Slack 工具（仅当配置了 `SLACK_USER_TOKEN` 时）
- 使用 `@tool(parse_docstring=True)` 装饰器自动生成工具 schema
- 工具内部通过 `backend.download_files` 获取沙箱中的文件，再通过 Slack SDK 发送

**安全最佳实践**：Slack token 保留在宿主机（不在沙箱内），敏感凭据不应进入沙箱环境。

#### 层 4：模型配置（第 81-87 行）

```python
model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `model` | `qwen3.5-plus` | 使用通义千问模型 |
| `base_url` | 环境变量 | 兼容 OpenAI API 格式的服务 |
| `temperature` | `0.7` | 创造性程度 |
| `max_tokens` | `2000` | 最大输出 token 数 |

**所有配置通过环境变量注入，符合 12-factor app 原则**。

#### 层 5：Agent 创建（第 89-93 行）

```python
agent = create_deep_agent(
    model=model,
    tools=tools,
    backend=backend,
)
```

这是整个文件的**最终产物**——通过 `create_deep_agent` 工厂函数创建一个完整的 Deep Agent 实例。

---

## 三、agent.py vs data_analysis_agent.py 对比

| 特性 | `agent.py` | `data_analysis_agent.py` |
|------|------------|--------------------------|
| **Checkpointer** | 无 | `InMemorySaver()` |
| **多轮对话** | 不支持 | 支持（通过 `thread_id`） |
| **运行方式** | `langgraph dev` 作为 graph 注册 | 直接 `python data_analysis_agent.py` 运行 |
| **Agent 创建参数** | `model`, `tools`, `backend` | 额外增加 `checkpointer` |
| **执行流程** | 被动响应请求 | 主动 `stream_events()` 执行并打印结果 |
| **Artifact 下载** | 无 | `backend.download_files(["/root/sales_analysis_plot.png"])` |
| **用途** | 生产环境 / dev server | 本地测试 / 调试 |

### data_analysis_agent.py 的额外功能

1. **Checkpointer**：`InMemorySaver()` 支持多轮对话状态持久化
2. **Thread 管理**：使用 `uuid7()` 生成唯一的 `thread_id`
3. **直接执行**：调用 `agent.stream_events()` 并打印结果
4. **Artifact 下载**：通过 `backend.download_files` 下载生成的图片

---

## 四、关键设计决策与潜在问题

### 4.1 模块级副作用

**问题**：`backend.upload_files()` 在模块导入时执行，不在任何函数内。

**影响**：
- `langgraph dev --reload` 热重载时每次代码变动都会重新上传
- 沙箱中已修改的文件会被覆盖
- 生产部署时每次 worker 启动都会执行

**改进建议**：改为惰性加载，仅在首次请求时上传数据，或通过工具由 agent 自主决定是否上传。

### 4.2 缺少 checkpointer

`agent.py` 不支持多轮对话。如果需要连续交互，应参考 `data_analysis_agent.py` 的 pattern 添加 `InMemorySaver`。

### 4.3 PATH 限制

```python
env={"PATH": "/usr/bin:/bin"}
```

此 PATH 设置是 Unix 风格。在 Windows 开发环境下可能导致 shell 命令失败。由于 `virtual_mode=True` 模拟了 Linux 环境，实际执行时可能通过 Docker 或 WSL 运行。

### 4.4 硬编码路径

`/root/data/sales_data.csv` 和 `/root/` 路径是 Unix 风格，在 Windows 本地测试时需要虚拟模式模拟。

---

## 五、相关文件清单

| 文件路径 | 角色 |
|----------|------|
| `src/data_analysis/agent.py` | 核心 Graph 定义，LangGraph dev server 注册入口 |
| `src/data_analysis/data_analysis_agent.py` | 完整可运行脚本，本地测试用 |
| `src/data_analysis/root/data/analyze_sales.py` | Agent 在沙箱中生成的分析脚本（版本 1） |
| `root/data/analyze_sales.py` | Agent 在沙箱中生成的分析脚本（版本 2） |
| `langgraph.json` | LangGraph 配置文件，注册 graph 路径 |
| `app.py` | LangGraph dev server 启动脚本 |

---

## 六、总结

本项目实现了一个典型的 **Data Analysis Deep Agent** 场景：

1. **Agent** 通过 `create_deep_agent` 创建，整合了 LLM、工具链和 Backend
2. **Backend**（`LocalShellBackend`）提供沙箱化的代码执行环境
3. **自定义工具**（Slack）扩展了 Agent 的外部交互能力
4. **数据流**：CSV 数据上传 -> Agent 分析 -> 执行 Python 脚本 -> 生成图表 -> 可选发送 Slack

架构简洁但有改进空间，主要是模块级副作用的消除和 checkpointer 的补充。
