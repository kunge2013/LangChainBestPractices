---
type: comparison
style: sketch-notes
aspect_ratio: "16:9"
references: []
description: "Before/After file split - single 779-line file vs 8 separate modules"
---

# 03 - Comparison - File Split

## LAYOUT

Split into two halves: LEFT (BEFORE) and RIGHT (AFTER), with a large hand-drawn arrow in the center labeled "拆分 Refactor →"

## BEFORE (LEFT HALF) - Red theme

A single massive file rectangle, colored red, filling the entire left side. Inside, show 8 smaller boxes crammed together and overlapping:

- Top of the file: "3.billing_manual_agent.py"
- Subtitle: "779 lines · 8 classes"
- Inside boxes (cramped, tight spacing):
  - "Config"
  - "DocxParser"
  - "ImageDescriber"
  - "VectorStoreBuilder"
  - "KnowledgeSearcher"
  - "GetSectionImages"
  - "BillingAgent"
  - "Pipeline + API"

Red warning badge at top: "⚠️ 单一文件 · 缺乏深度"

## AFTER (RIGHT HALF) - Green theme

8 neatly organized small file rectangles, arranged in a 2×4 grid, evenly spaced:

Each file card shows:
- Filename at top
- Line count estimate
- One-line description

Files (top row left to right):
- "config.py ~60 lines" - Configuration
- "docx_parser.py ~150 lines" - Document parsing
- "image_describer.py ~60 lines" - Image description
- "agent.py ~50 lines" - Agent creation

Files (bottom row left to right):
- "vector_store.py ~100 lines" - Vector store
- "tools.py ~130 lines" - LangChain tools
- "pipeline.py ~50 lines" - Pipeline orchestration
- "api.py ~25 lines" - API entry point

Green success badge at top: "✅ 8个独立模块 · 职责清晰"

## CENTER ARROW

Large hand-drawn arrow pointing left-to-right: "拆分 → 8 files · 100-200 lines each"

## COLORS

- BEFORE side: red background tint (#FEE2E2), red file outline (#ef4444)
- AFTER side: green background tint (#D1FAE5), green file outlines (#059669)
- Individual cards: soft pastel colors (blue, purple, orange, teal)
- Background: warm cream (#FFF8F0)

## STYLE

- Sketch-notes / hand-drawn style
- Warm cream paper background
- Black hand-drawn outlines
- Clear visual contrast between messy before and clean after
- Educational, professional tone
- Chinese labels throughout
