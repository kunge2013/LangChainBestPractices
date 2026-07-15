# `/coding-cap-ts` — 基于文档章节生成 TypeScript 代码

## Usage

```
/coding-cap-ts <path-to-doc-file>
```

示例:
```
/coding-cap-ts doc/ts/Deep\ Agents/1.Tools.md
```

## Description

根据 `doc/ts/Deep Agents/` 下的章节文档，在 `coding/ts/` 目录下生成对应的 TypeScript (langchain) 代码实现。

如果 `coding/ts/` 目录不存在，自动创建。
如果目标章节目录不存在，自动创建。

## 目录结构映射

文档文件名自动映射为章节目录名:

| 文档文件                                  | 章节目录                              |
| --------------------------------------- | ------------------------------------- |
| `1.Tools.md`                            | `coding/ts/Chapter_1_Tools/`          |
| `2.Backends.md`                         | `coding/ts/Chapter_2_Backends/`       |
| `6.1.Dynamic subagents.md`              | `coding/ts/Chapter_6_1_Dynamic_subagents/` |
| `19.Sandbox.md`                         | `coding/ts/Chapter_19_Sandbox/`       |

映射规则:
1. 从文件名提取序号和主题（如 `1.Tools` → 序号 `1`, 主题 `Tools`）
2. 主题中的空格、点号替换为下划线
3. 格式: `Chapter_{序号}_{主题}`，序号含子章节号（如 `6_1`）

### 完整目录结构

```
coding/
└── ts/
    ├── llm_config.ts                      # 全局 LLM 配置（所有章节共享，首次生成时创建）
    ├── Chapter_1_Tools/
    │   ├── README.md                      # 章节说明：每个文件的作用 + 代码文件列表
    │   ├── Chapter_1_Tools_SUMMARY.md     # 代码摘要（中文）
    │   ├── 01_custom_tools.ts             # 序号前缀 + 英文功能名
    │   ├── 02_mcp_tools.ts
    │   └── 03_builtin_tools.ts
    ├── Chapter_2_Backends/
    │   ├── README.md
    │   ├── Chapter_2_Backends_SUMMARY.md
    │   └── 01_backend_setup.ts
    └── ...
```

## Instructions

### 1. 解析输入文件

从 `<path-to-doc-file>` 提取章节序号和主题，确定目标目录 `coding/ts/Chapter_{N}_{Topic}/`。

如果文件路径不在 `doc/ts/Deep Agents/` 下，提示用户并终止。

### 2. 创建目录结构

- 如果 `coding/ts/` 不存在，创建它
- 如果 `coding/ts/llm_config.ts` 不存在，创建全局 LLM 配置模板（使用 `@langchain/openai` 的 `ChatOpenAI`，从环境变量读取 API key）
- 创建目标章节目录 `coding/ts/Chapter_{N}_{Topic}/`

### 3. 生成代码文件

根据章节文档内容，生成对应的 TypeScript 代码文件:

- 每个功能点生成一个 `.ts` 文件，文件名为英文，描述功能用途
- 文件名带序号前缀，从 `01` 开始，按功能顺序递增（`01_xxx.ts`, `02_xxx.ts`, ...）
- 所有代码基于 TypeScript langchain / langgraph 实现
- 代码中 LLM 配置统一 import `coding/ts/llm_config.ts`
- 每个代码文件顶部添加注释说明对应文档的哪个部分
- 代码使用 ESM 模块语法（`import/export`），与 `typescript/package.json` 中 `"type": "module"` 一致

命名格式: `{序号}_{功能英文名}.ts`

### 4. 生成章节 README.md

在 `coding/ts/Chapter_{N}_{Topic}/README.md` 中说明:

- 本章节对应哪个文档
- 本章节涵盖哪些核心概念
- 每个 `.ts` 文件的作用简述
- 文件列表（带链接/路径）

### 5. 生成代码摘要

基于生成的代码 + 原始章节文档内容，生成摘要文件:

- 文件名: `Chapter_{N}_{Topic}_SUMMARY.md`
- 位置: `coding/ts/Chapter_{N}_{Topic}/Chapter_{N}_{Topic}_SUMMARY.md`

#### 摘要格式要求

```markdown
# {范式名/主题名}

## 概述

（中文描述：这个范式/模式是什么，解决什么问题）

## 流程

```mermaid
（用 mermaid 语法绘制该范式的流程图）
```

## 代码范式说明

### 范式名称

- **使用场景**: （何时使用该模式）
- **核心思想**: （模式的核心逻辑）

#### 代码示例

```typescript
（完整的流程代码，展示范式如何使用）
```

#### 范式分析

（说明代码中用到了什么设计范式/agentic 模式）
```

具体要求:
1. **语言**: 全部使用中文描述
2. **标题**: 一级标题仅为范式名/主题名，不带任何额外修饰（如 "路由模式"，不允许 "路由模式-代码摘要"）
3. **层级**: 使用 4 级标题结构，层次清晰
4. **代码块**: 包含完整可理解的流程代码
5. **流程图**: 必须包含 mermaid 流程图
6. **范式总结**: 说明每个代码段用到的设计范式及使用场景

### 6. 维护依赖

检查生成的代码文件是否引入了 `typescript/package.json` 的 `dependencies` 中不存在的包:
- 如果是 langchain 生态的已有包，确保已在 `dependencies` 中
- 如果引入了全新包，提示用户运行 `npm install <package>` 手动添加
