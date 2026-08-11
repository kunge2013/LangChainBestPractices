# Tasks: Multimodal Billing Manual Agent

## Phase 1: Setup

- [x] 1.1 Create `requirements-billing-manual.txt` with all dependencies
- [x] 1.2 Create `3.billing_manual_agent.py` file with imports and `.env` loading
- [x] 1.3 Create `output/images/` directory structure
- [x] 1.4 Add `.env` template with `QWEN_API_KEY`, `QWEN_BASE_URL`, `QWEN_MODEL_NAME`

## Phase 2: Document Parser

- [x] 2.1 Implement `parse_docx(docx_path, output_dir)` function
  - Sequentially iterate `doc.paragraphs` and `doc.inline_shapes`
  - Extract images and save as PNG with sequential naming (`img_0.png`, `img_1.png`, ...)
  - Record nearest paragraph index for each image
  - Return structured data: `List[Dict]` with type, text, image_path, nearest_paragraph_index
- [ ] 2.2 Test parser with the billing manual `.docx` file
  - Verify all images extracted
  - Verify paragraph-image associations are reasonable

## Phase 3: Image Description Generator

- [x] 3.1 Implement `describe_image(image_path, client)` function
  - Read image file, encode to base64
  - Call qwen3.6 vision API via OpenAI protocol
  - Return Chinese description
- [x] 3.2 Implement `describe_all_images(image_refs, client)` with retry logic
  - Process images sequentially (avoid rate limiting)
  - Retry up to 3 times with exponential backoff on API failures
  - Log progress for each image
- [ ] 3.3 Test with a few sample images from the manual

## Phase 4: Vector Store Builder

- [x] 4.1 Implement text chunking
  - Use `RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=300)`
  - Associate images with their nearest chunk (by paragraph index proximity)
  - Each chunk metadata: `{text, image_descriptions, image_paths, source, chunk_index}`
- [x] 4.2 Implement `build_vector_store(chunks, embeddings, force_recreate=False)`
  - Check for existing index (reuse if available)
  - Create new index from chunks with metadata
  - Embedding model: `shibing624/text2vec-base-chinese`
- [x] 4.3 Implement `search_knowledge(query, db, k=3)` tool function
  - Perform similarity search
  - Format results: text + image descriptions + image paths
  - Return formatted string for agent consumption

## Phase 5: Agent Creation

- [x] 5.1 Implement `create_billing_agent(db, model_config)` using `create_deep_agent`
  - Configure system prompt with billing manual context
  - Include image path prefix (`output/images/`) in prompt
  - Attach `search_knowledge` tool
- [x] 5.2 Wire up the main interactive loop
  - User asks question → agent responds with text + image paths
  - Support multi-turn conversation

## Phase 6: Integration & Testing

- [ ] 6.1 Run full pipeline: parse → describe → build → agent
  - Test with sample questions: "如何创建新客户?", "账单生成流程是什么?", "如何查看欠费信息?"
  - Verify images are correctly associated with answers
- [ ] 6.2 Edge case testing
  - Query with no matching results
  - Query about images specifically ("这个界面长什么样?")
  - Query about procedures with multiple steps
- [ ] 6.3 Clean up and document usage
