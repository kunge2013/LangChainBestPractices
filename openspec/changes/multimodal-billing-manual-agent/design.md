# Design: Multimodal Billing Manual Agent

## Architecture

```
.docx 文件
  → python-docx 解析 (顺序遍历段落+图片)
    → 图片提取 → output/images/img_N.png
      → qwen3.6 生成图片描述 (OpenAI 协议)
        → RecursiveCharacterTextSplitter (1500/300)
          → Neo4j 向量库 (text + image_descriptions + image_paths)
            → create_deep_agent + search_knowledge tool
              → 用户提问 → agent 自主检索 → 返回文本答案 + 图片路径
```

## Components

### 1. Document Parser (`parse_docx`)

Uses `python-docx` to iterate through document elements in order:

```python
from docx import Document

doc = Document(docx_path)
elements = []
for para in doc.paragraphs:
    elements.append(("paragraph", para.text, para._p))

# Images are in inline shapes
for shape in doc.inline_shapes:
    # Extract image blob from shape
    # Find nearest paragraph by position
    elements.append(("image", image_bytes, nearest_paragraph_index))
```

**Key decisions:**
- Images extracted as PNG and saved to `output/images/img_N.png` (sequential numbering)
- Each image is associated with the nearest paragraph by XML position
- The association is recorded as `image_paragraph_index`

### 2. Image Description Generator (`describe_images`)

Uses qwen3.6 via OpenAI protocol:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("QWEN_API_KEY"),
    base_url=os.environ.get("QWEN_BASE_URL")
)

def describe_image(image_path: str) -> str:
    # Encode image to base64
    # Call vision API with image + prompt: "请用中文描述这张图片的内容，包括图片中的文字、流程、步骤等"
    # Return the description
```

**Config from `.env`:**
- `QWEN_API_KEY` — API key
- `QWEN_BASE_URL` — e.g., `https://dashscope.aliyuncs.com/compatible-mode/v1`
- `QWEN_MODEL_NAME` — e.g., `qwen-vl-max`

### 3. Vector Store Builder (`build_vector_store`)

Text splitting + Neo4j ingestion:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector

splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
chunks = splitter.split_documents(docs)

# Each chunk's metadata includes image info:
#   - text: chunk content
#   - image_descriptions: ["图片1描述：...", "图片2描述：..."]
#   - image_paths: ["output/images/img_0.png", "output/images/img_1.png"]
#   - source: "billing_manual"
```

**Neo4j node structure:**
```
Node {
    text: "操作流程说明...",
    image_descriptions: ["图1显示了账单生成界面...", "图2显示了审核流程..."],
    image_paths: ["output/images/img_0.png", "output/images/img_1.png"],
    source: "billing_manual",
    chunk_index: 0
}
```

**Embedding model:** `shibing624/text2vec-base-chinese` (reused from existing code)

### 4. Agent (`create_agent`)

Uses `from deepagents import create_deep_agent`:

```python
from deepagents import create_deep_agent

def search_knowledge(query: str) -> str:
    """检索政企计费账务系统操作手册的知识库"""
    results = db.similarity_search_with_score(query, k=3)
    # Format results with text + image paths
    return formatted_results

agent = create_deep_agent(
    model="qwen3.6",
    tools=[search_knowledge],
    system_prompt="""你是一个政企计费账务系统操作助手。
你可以使用 search_knowledge 工具来检索操作手册的内容。
检索结果包含相关文本和关联图片路径。
回答用户问题时，请同时提供文字说明和相关图片路径。
图片存储在 output/images/ 目录下。"""
)
```

## File Structure

```
17.neo4j_agent/
├── 2.neo4j-hfEmbdLangchain.py    # 保留不动
├── 3.billing_manual_agent.py     # 新增：主脚本（4个阶段）
└── output/
    └── images/                   # 提取的图片目录
        ├── img_0.png
        ├── img_1.png
        └── ...
```

## Dependencies

New/updated packages in `requirements-billing-manual.txt`:

```
python-docx>=1.1.0
langchain-huggingface
langchain-neo4j
langchain-openai          # qwen3.6 OpenAI 协议交互
deepagents
python-dotenv
Pillow                    # 图片处理
```

## Data Flow

```
Stage 1: parse_docx()
  Input: .docx file path
  Output: List[TextChunk | ImageRef] + saved images

Stage 2: describe_images()
  Input: List[ImageRef]
  Output: List[ImageRef with description]

Stage 3: build_vector_store()
  Input: TextChunks + ImageRefs with descriptions
  Output: Neo4jVector instance

Stage 4: create_agent()
  Input: Neo4jVector + config
  Output: DeepAgent instance ready for interaction
```

## Error Handling

- **docx parsing fails** — fallback: skip the problematic element, log warning
- **image description API fails** — retry with exponential backoff (max 3), then mark as "描述生成失败"
- **Neo4j connection fails** — clear error message with connection details
- **No results found** — agent suggests rephrasing the query
