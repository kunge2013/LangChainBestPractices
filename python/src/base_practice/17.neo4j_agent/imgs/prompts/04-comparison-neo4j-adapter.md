---
type: comparison
style: sketch-notes
aspect_ratio: "16:9"
references: []
description: "Before/After Neo4j connection unification - dual paths vs single adapter"
---

# 04 - Comparison - Neo4j Adapter

## LAYOUT

Split into two halves: LEFT (BEFORE) and RIGHT (AFTER), with a large hand-drawn arrow in the center labeled "统一 Adapter →"

## BEFORE (LEFT HALF) - Red theme

**Config** at top center (yellow/orange)

From Config, TWO separate paths flow downward:

**Path A (left)**:
- "VectorStoreBuilder" → "Neo4jVector (LangChain wrapper)" → Neo4j database icon

**Path B (right)**:
- "GetSectionImages" → "GraphDatabase.driver() (Raw driver)" → same Neo4j database icon

Both paths converge on the same Neo4j database cylinder icon at the bottom.

Red warning callout box:
"⚠️ 重复创建连接"
- 两条独立的 Neo4j 连接路径
- 连接池无法统一管理
- 配置变更需修改两处
- 绕过 LangChain 封装层

## AFTER (RIGHT HALF) - Green theme

**Config** at top center (yellow/orange)

From Config, a single path flows to a central green module:

**"Neo4jAdapter"** - a large green rounded rectangle, centered, with icon of a connector/plug

From Neo4jAdapter, arrows branch to both:
- "VectorStoreBuilder" → Neo4j
- "GetSectionImages" → Neo4j

Single Neo4j database icon at the bottom.

Green success callout box:
"✅ 统一连接管理"
- 单一连接，连接池复用
- 配置变更只需一处
- 统一错误处理
- 可测试性提升

## CENTER ARROW

Large hand-drawn arrow: "统一 → Neo4jAdapter"

## COLORS

- BEFORE side: red background tint (#FEE2E2), red warning elements (#ef4444)
- AFTER side: green background tint (#D1FAE5), green adapter module (#059669)
- Neo4j database: purple (#7c3aed)
- Config: yellow/orange (#f59e0b)
- Arrows: black, hand-drawn
- Background: warm cream (#FFF8F0)

## STYLE

- Sketch-notes / hand-drawn style
- Warm cream paper background
- Black hand-drawn outlines
- Soft pastel blocks behind modules
- Clear problem/solution contrast
- Technical architecture diagram feel
- Chinese labels throughout
