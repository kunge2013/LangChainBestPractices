<!-- [AGC:FILE] tool=Cc author=fangkun date=2026-08-24 -->

# 多 Agent 协同开发模块 — 设计文档

> **模块位置**: `python/src/base_practice/19.multi-agent/`
> **日期**: 2026-08-24
> **状态**: 设计评审中

---

## 1. 概述

本模块实现一个基于 LangGraph 的多 Agent 协同工作流，由两个 Agent 协作完成代码开发与测试：

- **Agent1（Developer）**：根据设计文档 + 用户需求实现代码开发
- **Agent2（Tester）**：对 Agent1 产出的代码进行混合测试（pytest 单元测试 + LLM 代码审查）

两者形成 `develop → test_and_evaluate → fix` 的迭代循环，直到代码质量达标或达到最大轮数。

---

## 2. 技术栈

| 组件 | 选型 | 版本 |
|------|------|------|
| 编程语言 | Python | >= 3.12 |
| 编排框架 | LangChain + LangGraph | langchain 1.3.x, langgraph 1.2.x |
| LLM 模型 | 可配置（默认 gpt-4o） | langchain-openai / langchain-anthropic |
| 测试框架 | pytest | - |
| 代码检查 | ruff, mypy | - |
| 环境管理 | conda | langchain11 |

---

## 3. 系统架构

### 3.1 编排方式

采用 **LangGraph 状态图** 作为核心编排引擎，利用其：

- 状态持久化（checkpointer）
- 条件边路由
- 可视化调试
- 可部署为 API

### 3.2 状态图拓扑

```
┌─────────┐     ┌──────────┐     ┌───────────────────────┐
│  START   │────▶│ develop  │────▶│ test_and_evaluate      │
└─────────┘     └──────────┘     └──────────┬────────────┘
                          ▲                  │
                          │    ┌─────────────┤
                          │    │             │
                          └────┤ fix    │   DONE    │
                               └─────────┘   └─────────┘
```

#### 节点说明

| 节点 | 执行者 | 职责 |
|------|--------|------|
| `develop` | Agent1 | 读取设计文档，生成/修改代码文件 |
| `test_and_evaluate` | Agent2 | 生成 pytest 测试用例并运行 + LLM 代码审查；内部评估：CRITICAL/HIGH = 0 → DONE，否则 → fix |
| `fix` | Agent1 | 根据 bug_list 修复代码，然后回到 test_and_evaluate |

#### 终止条件

- **质量达标提前退出**：CRITICAL 和 HIGH 级别 bug 数量 = 0 → 进入 DONE
- **最大轮数兜底**：`iteration_count >= max_rounds` → 强制 DONE，状态标记 `FAILED`

### 3.3 数据流

```
设计文档 (Markdown)  ──┐
用户补充需求          ──┼──▶ [develop] ──▶ code_artifact ──▶ [test_and_evaluate]
                       │                                            │
                       │                                     ┌──────┴──────┐
                       │                                     │test_results  │
                       │                                     │bug_list      │
                       │                                     └──────┬──────┘
                       │                                            │
                       │              ┌─────────────────────────────┤
                       │              │                             │
                       │         [fix]                          [DONE]
                       │              │                             │
                       │              └──▶ 回到 test_and_evaluate   │
                       │                                            │
                       │                                     ┌──────▼──────┐
                       │                                     │  输出报告    │
                       │                                     │test_report  │
                       │                                     │code_logic   │
                       │                                     └─────────────┘
```

---

## 4. 状态定义

使用 `TypedDict` 定义 LangGraph 状态：

```python
class AgentState(TypedDict):
    # ---- 通信 ----
    messages: list[BaseMessage]        # Agent 间自然语言沟通

    # ---- 输入 ----
    design_doc: str                    # 设计文档内容
    requirement: str                   # 用户补充需求

    # ---- 工件 ----
    code_artifact: dict[str, str]      # {文件路径: 文件内容}
    test_results: dict                 # pytest 结果 + LLM 审查结果
    bug_list: list[BugItem]            # [{severity, description, file, line}]

    # ---- 控制 ----
    iteration_count: int               # 当前轮次（从 1 开始）
    max_rounds: int                    # 最大轮数（默认 5）
    status: str                        # "IN_PROGRESS" | "PASSED" | "FAILED"

    # ---- 输出 ----
    output_dir: str                    # 输出根目录
    review_dimensions: list[str]       # LLM 审查维度列表
```

---

## 5. Agent 定义

### 5.1 Agent1 — Developer（开发者）

| 属性 | 值 |
|------|-----|
| 角色 | 代码开发者 |
| 模型 | 可配置，默认 `gpt-4o` |
| System Prompt | 注入设计文档全文 + 编码规范指引 |
| 工具集 | `read_file`, `write_file`, `edit_file`, `run_command` |

**工具说明：**

| 工具 | 参数 | 说明 |
|------|------|------|
| `read_file(path)` | 文件路径 | 读取工作目录中的文件内容 |
| `write_file(path, content)` | 路径 + 内容 | 创建新文件 |
| `edit_file(path, old, new)` | 路径 + 原文 + 替换 | 修改已有文件 |
| `run_command(cmd)` | shell 命令 | 执行 `ruff check`、`mypy`、`pytest` 等 |

### 5.2 Agent2 — Tester（测试者）

| 属性 | 值 |
|------|-----|
| 角色 | 测试工程师 + 代码审查员 |
| 模型 | 可配置，默认 `gpt-4o` |
| System Prompt | 注入审查维度 + 输出格式要求 |
| 额外工具 | 无（通过 LLM 推理生成测试代码和审查结果，写入状态字段） |

**LLM 审查维度（默认可配置）：**

1. **功能正确性** — 代码是否实现了设计文档中描述的功能
2. **代码质量** — PEP 8、类型安全、错误处理、命名规范
3. **边界情况** — 空值处理、异常输入、类型边界

### 5.3 Bug 严重性分级

| 级别 | 含义 | 是否阻塞 |
|------|------|----------|
| `CRITICAL` | 功能缺陷、运行时崩溃、数据丢失 | ✅ 必须修复 |
| `HIGH` | 逻辑错误、安全隐患、严重性能问题 | ✅ 必须修复 |
| `LOW` | 代码风格、命名建议、优化建议 | ❌ 仅记录 |

---

## 6. 输入与输出

### 6.1 输入

| 输入项 | 格式 | 传入方式 |
|--------|------|----------|
| 设计文档 | Markdown 文件 | CLI 参数 `--design ./path/to/design.md`（读取文件内容注入 system prompt） |
| 补充需求 | 字符串 | CLI 参数 `--requirement "额外需求描述"` |

### 6.2 输出

所有输出到用户指定的 `output_dir`（默认 `./output/{timestamp}/`）：

| 文件 | 格式 | 内容 | 生成时机 |
|------|------|------|----------|
| `test_report.md` | Markdown | 测试概览、bug 列表、迭代历史、最终状态 | 每轮更新 |
| `test_report.json` | JSON | 结构化测试数据 | 每轮更新 |
| `code_logic.md` | Markdown | 模块概览 + 函数级文档 | 仅最终轮（DONE） |
| `code/` | 目录 | 生成的源代码文件 | 每轮更新 |
| `tests/` | 目录 | Agent2 生成的测试用例 | 每轮更新 |

### 6.3 测试报告格式

**Markdown 报告结构：**

```markdown
# 测试报告
## 概览
- 状态: PASSED / FAILED
- 迭代轮数: 3
- 最终 CRITICAL/HIGH bug: 0

## Bug 列表
### CRITICAL
（无）
### HIGH
（无）
### LOW
1. [LOW] 函数命名不符合 PEP 8 (utils.py:15)

## 测试结果
| 测试用例 | 状态 | 耗时 |
|----------|------|------|
| test_xxx | ✅ PASS | 0.02s |
| test_yyy | ✅ PASS | 0.01s |

## 迭代历史
- Round 1: 3 CRITICAL, 2 HIGH → fix
- Round 2: 0 CRITICAL, 1 HIGH → fix
- Round 3: 0 CRITICAL, 0 HIGH → PASSED
```

**JSON 报告结构：**

```json
{
  "status": "PASSED",
  "total_rounds": 3,
  "iterations": [...],
  "bugs": [...],
  "test_summary": {"passed": 10, "failed": 0, "total": 10}
}
```

### 6.4 代码逻辑文档结构

```markdown
# 代码逻辑文档
## 模块概览
- 文件结构 + 每个文件职责

## 函数文档
### file: utils.py
#### `def process_data(input: str) -> dict`
- **参数**: input - 原始数据字符串
- **返回值**: 处理后的字典结构
- **核心逻辑**: 1. 解析输入 2. 数据清洗 3. 结构化输出
```

---

## 7. 配置参数

通过 `config.py` 定义，支持环境变量和 CLI 参数覆盖：

| 参数 | 默认值 | 环境变量 | 说明 |
|------|--------|----------|------|
| `developer_model` | `gpt-4o` | `DEV_MODEL` | Agent1 使用的 LLM |
| `tester_model` | `gpt-4o` | `TEST_MODEL` | Agent2 使用的 LLM |
| `max_rounds` | `5` | `MAX_ROUNDS` | 最大迭代轮数 |
| `review_dimensions` | `["correctness", "quality", "edge_cases"]` | - | LLM 审查维度 |
| `output_dir` | `./output/{timestamp}` | `OUTPUT_DIR` | 输出根目录 |
| `enable_hitl` | `False` | `ENABLE_HITL` | 是否启用 HITL（预留） |
| `conda_env` | `langchain11` | `CONDA_ENV` | pytest 运行环境 |

---

## 8. 异常与兜底

| 场景 | 处理方式 |
|------|----------|
| 达到 `max_rounds` 仍有 CRITICAL/HIGH bug | 强制 DONE，状态标记 `FAILED`，生成部分报告（含未修复 bug） |
| pytest 运行失败（语法错误、导入失败等） | 作为 CRITICAL bug 记入 `bug_list`，由 Agent1 在 fix 阶段修复 |
| Agent 工具调用失败 | 错误信息反馈给 Agent，允许重试一次 |
| 设计文档为空或无法读取 | 启动时校验，立即报错退出 |
| LLM 返回格式不符合预期 | 要求 Agent 重新生成，最多重试 2 次 |

---

## 9. HITL 预留设计

在 `test_and_evaluate` 节点中预留 `interrupt` 接口：

```python
# 伪代码
def test_and_evaluate(state: AgentState) -> AgentState:
    # ... 测试 + 审查逻辑 ...

    if config.enable_hitl:
        # 预留：暂停等待人工确认
        interrupt({"bug_list": state["bug_list"], "action": "approve_or_fix"})

    # 评估逻辑...
```

- V1 默认 `enable_hitl = False`，全自动运行
- 后续只需改配置即可开启人工审批
- 与 `15.multi-agent/` 中的 HITL 模式保持一致

---

## 10. 文件结构

```
19.multi-agent/
├── __init__.py            # 模块初始化
├── graph.py               # LangGraph 状态图定义（3 节点 + 条件边）
├── agents.py              # Agent1（developer）和 Agent2（tester）定义
├── tools.py               # Agent1 工具集（read_file, write_file, edit_file, run_command）
├── prompts.py             # System prompt 模板（Agent1、Agent2、审查维度）
├── models.py              # TypedDict 状态 + Pydantic 模型（BugItem, TestResult, TestReport）
├── report.py              # 报告生成器（Markdown + JSON 双格式）
├── config.py              # 可配置参数（模型名、轮数、维度、目录等）
└── run.py                 # CLI 入口
```

每个文件控制在 **200-400 行**，符合项目编码规范。

---

## 11. CLI 入口

```bash
# 基本用法
python run.py --design ./design.md

# 完整参数
python run.py \
  --design ./design.md \
  --requirement "使用异步方式处理，支持并发" \
  --output ./output/my-feature \
  --max-rounds 5 \
  --model gpt-4o \
  --review-dimensions correctness,quality,edge_cases
```

---

## 12. 与现有模块的关系

| 参考模块 | 借鉴点 |
|----------|--------|
| `15.multi-agent/` | supervisor 模式、工具包装 Agent、HITL 模式 |
| `7.stategraph-checkpointer.py` | LangGraph StateGraph + checkpointer 用法 |
| `14.SQL-Agent-HITL.py` | HITL interrupt/resume 模式 |
| TypeScript `deepagents` ch.13-16 | subagent 通信、streaming、HITL 模式（参考设计） |

---

## 13. 未来扩展

- **HITL 启用**：改配置即可开启人工审批
- **更多 Agent**：可扩展 Agent3（安全审查）、Agent4（性能分析）
- **远程沙箱**：将 pytest 执行从宿主机迁移到 Docker / E2B
- **CI/CD 集成**：JSON 报告接入 GitHub Actions 等
- **LangSmith 集成**：添加 tracing，按 Agent 过滤运行记录
