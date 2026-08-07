---
type: framework
style: sketch-notes
aspect_ratio: "16:9"
references: []
description: "Module dependency map - 8 classes with Config at center"
---

# 02 - Framework - Module Dependencies

## ZONES

**TOP CENTER**: "Config" module - a yellow/orange rounded rectangle, labeled "Config 配置管理". This is the central hub that all other modules depend on. Arrows radiate downward from Config to every other module.

**MIDDLE ROW - Data Layer**: Three modules side by side:
- "DocxParser 文档解析" (blue)
- "ImageDescriber 图片描述" (green)
- "VectorStoreBuilder 向量库构建" (purple)

**MIDDLE ROW - Tools Layer**: Two modules:
- "KnowledgeSearcher 知识检索" (light blue)
- "GetSectionImages 章节检索" (teal)

**BOTTOM ROW - Agent Layer**:
- "BillingAgent Agent创建" (red)

**BOTTOM CENTER**: Two modules:
- "BillingManualPipeline 主流程" (dark red)
- "build_agent() API入口" (purple)

## CONNECTIONS

- Config → ALL modules (dashed lines, showing config dependency)
- DocxParser → Pipeline (solid arrow)
- ImageDescriber → Pipeline (solid arrow)
- VectorStoreBuilder → Pipeline + API (solid arrows)
- KnowledgeSearcher → BillingAgent (solid arrow)
- GetSectionImages → BillingAgent (solid arrow)
- BillingAgent → Pipeline + API (solid arrows)
- Pipeline → API (solid arrow)

## LABELS

Each module shows its Chinese name + brief English description.
Layer labels on the left: "数据层", "工具层", "Agent层", "编排层"

## COLORS

- Config: yellow/orange (#f59e0b) - highlighted as center
- Data layer: blue, green, purple (#2563eb, #059669, #7c3aed)
- Tools layer: light blues (#38bdf8, #14b8a6)
- Agent layer: red (#dc2626)
- Orchestration: dark red + purple (#b91c1c, #6d28d9)
- Background: warm cream (#FFF8F0)

## STYLE

- Sketch-notes / hand-drawn style
- Warm cream paper background
- Black hand-drawn outlines
- Soft pastel blocks behind modules
- Dependency arrows in black, hand-drawn style
- Clear layer separation with subtle horizontal dividers
- Educational, architectural diagram feel
