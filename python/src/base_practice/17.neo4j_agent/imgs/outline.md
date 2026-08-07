---
type: mixed
density: per-section
style: sketch-notes
palette: default
image_count: 4
language: zh
---

# Illustration Outline

## Illustration 1
**Position**: 完整业务流程 section
**Purpose**: 可视化 docx → Neo4j → Agent 问答的完整数据流水线
**Visual Content**: 从左到右的数据流：左侧是 .docx 文档图标，经过解析器（齿轮图标）提取文本段落和图片，调用 VL 模型生成描述，文本分块后向量化，存入 Neo4j 数据库（圆柱图标），最终通过 Agent 提供问答检索
**Filename**: 01-infographic-business-flow.png

## Illustration 2
**Position**: 当前模块依赖图 section
**Purpose**: 可视化 8 个类之间的依赖关系，展示 Config 的中心化作用
**Visual Content**: 架构图：Config 位于顶部中心，下方分为三层——数据层（DocxParser, ImageDescriber, VectorStoreBuilder）、工具层（KnowledgeSearcher, GetSectionImages）、Agent 层（BillingAgent），底部是 Pipeline 和 API 入口，箭头表示依赖方向
**Filename**: 02-framework-module-dependencies.png

## Illustration 3
**Position**: 架构摩擦点 1 — 文件拆分 section
**Visual Content**: 左右对比图——左侧是一个巨大的单一文件（779 行，8 个类挤在一起，用红色标记），右侧是 8 个整齐排列的小文件，每个文件有明确职责（100-200 行），用绿色标记。中间有箭头标注"拆分"
**Filename**: 03-comparison-file-split.png

## Illustration 4
**Position**: 架构摩擦点 2 — Neo4j 连接统一 section
**Visual Content**: 左右对比图——左侧展示两条独立的 Neo4j 连接路径（一条通过 LangChain 封装，一条通过原生驱动），用红色标记重复连接问题；右侧展示统一的 Neo4jAdapter 居中管理，两条路径都通过它连接，用绿色标记统一连接
**Filename**: 04-comparison-neo4j-adapter.png
