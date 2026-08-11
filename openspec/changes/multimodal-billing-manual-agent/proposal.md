# Change: Multimodal Billing Manual Agent

## What

Build a multimodal knowledge retrieval agent for the 中国电信集团政企计费账务系统操作手册 (China Telecom Government & Enterprise Billing System Operations Manual). The agent answers user questions by retrieving relevant text and images from the manual, using Neo4j as a vector store and qwen3.6 (via OpenAI protocol) for image description generation.

## Why

The existing `2.neo4j-hfEmbdLangchain.py` script only supports web page text retrieval using LangChain + Neo4j vectors. The billing operations manual contains critical procedural text AND images (screenshots, diagrams, flowcharts) that are equally important for answering operational questions. A text-only approach is insufficient — users need to see the actual screenshots from the manual when asking how to perform specific operations.

## Current State

- `2.neo4j-hfEmbdLangchain.py` — retrieves web news using Neo4j vectors + HuggingFace embeddings
- `python-docx` available for `.docx` parsing
- qwen3.6 accessible via OpenAI protocol
- No image processing pipeline exists
- No agent-based interaction exists

## Proposed Changes

1. **Document parser** — extract text and images from the `.docx` manual using `python-docx`
2. **Image description generator** — use qwen3.6 (OpenAI protocol) to generate Chinese descriptions for each extracted image
3. **Multimodal vector store builder** — store text chunks + image descriptions + image paths together in Neo4j nodes
4. **Deep agent** — create a `create_deep_agent` instance with a `search_knowledge` tool that retrieves both text and images

## Non-Goals

- Building a web UI for the agent
- Supporting other document formats (PDF, `.doc`)
- Real-time document updates (manual rebuild requires explicit trigger)
- Multi-manual support (single manual only for now)

## Success Criteria

- User can ask a question about the billing system and receive a text answer with relevant image file paths
- All images from the manual are extractable and have meaningful descriptions
- The agent can autonomously decide to search with different queries to find the best results
