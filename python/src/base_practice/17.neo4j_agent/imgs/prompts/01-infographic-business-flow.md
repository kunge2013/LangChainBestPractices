---
type: infographic
style: sketch-notes
aspect_ratio: "16:9"
references: []
description: "System architecture data flow - docx to Neo4j to Agent Q&A"
---

# 01 - Infographic - Business Flow

## ZONES

**LEFT ZONE**: A .docx document file icon with Chinese text label "政企计费账务系统操作手册.docx". Show it as a paper document with a blue folder icon.

**TOP CENTER ZONE**: Processing pipeline shown as sequential stages:
- Stage 1: "DocxParser" - magnifying glass over document, extracting text paragraphs (lines of text) and images (small rectangles)
- Stage 2: "ImageDescriber" - AI brain icon (qwen VL model), generating text descriptions for images
- Stage 3: "TextSplitter" - scissors cutting long text into smaller chunks
- Stage 4: "Embeddings" - mathematical vector arrows, labeled "HuggingFace text2vec"

**RIGHT ZONE**: Neo4j database cylinder icon in purple, labeled "Neo4j 向量库", with multiple document nodes inside showing "chunk" nodes connected by edges.

**BOTTOM RIGHT ZONE**: "BillingAgent" - robot head icon with speech bubble "用户问答", showing two tools underneath: "KnowledgeSearcher" (search icon) and "GetSectionImages" (image grid icon). An arrow flows from Neo4j to the agent.

## FLOW ARROWS

Connect stages left-to-right with thick hand-drawn arrows:
docx → Parser → Describer → Splitter → Embeddings → Neo4j → Agent → 用户问答

## LABELS

- "📄 操作手册.docx"
- "DocxParser - 解析文本段落 + 提取图片"
- "ImageDescriber - qwen VL 模型生成图片描述"
- "RecursiveCharacterTextSplitter - 文本分块"
- "HuggingFace Embeddings - 向量化"
- "Neo4jVector - 存入向量库"
- "BillingAgent - 创建 Deep Agent"
- "KnowledgeSearcher - 向量相似度检索"
- "GetSectionImages - 按章节查询"
- "用户问答" (at the end)

## COLORS

- Document blue (#2563eb)
- Parser orange (#f59e0b)
- Describer purple (#7c3aed)
- Neo4j purple (#7c3aed)
- Agent red (#dc2626)
- End result green (#059669)
- Background: warm cream (#FFF8F0)

## STYLE

- Sketch-notes / hand-drawn style
- Warm cream paper background
- Black hand-drawn lines and outlines
- Soft pastel colored blocks behind each stage
- Labels in Chinese, handwritten style
- Clean, educational infographic layout
- Professional but approachable feel
