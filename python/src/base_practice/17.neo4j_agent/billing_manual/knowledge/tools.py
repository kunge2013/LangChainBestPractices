# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual.knowledge.tools
===============================
LangChain tools for retrieving knowledge from the Neo4j vector store.

- KnowledgeSearcher  — similarity search by query text
- GetSectionImages   — retrieve all content for a named section

Adapted from 3.billing_manual_agent.py :: KnowledgeSearcher, GetSectionImages.
"""

import json
import logging
import os
from typing import Any

from langchain_core.tools import BaseTool
from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector
from neo4j import GraphDatabase

from ..config import Config
from ..exceptions import VectorStoreError

logger = logging.getLogger(__name__)

# [AGC:START] tool=Cc author=fangkun


# ── shared utility ──────────────────────────────────────────────────────────


def _image_to_html(config: Config, image_path: str, alt: str = "") -> str:
    """Convert an image path to an HTML ``<img>`` tag.

    Uses a configurable base URL so no base64 embedding is needed.
    """
    if not image_path or not os.path.exists(image_path):
        return ""
    return (
        f'<img src="{config.image_base_url}/{os.path.basename(image_path)}" alt="{alt}" />'
    )


# ── KnowledgeSearcher ───────────────────────────────────────────────────────


class KnowledgeSearcher(BaseTool):
    """Retrieve knowledge by vector similarity search."""

    name: str = "search_knowledge"
    description: str = (
        "检索操作手册的知识库。返回相关文本内容、所属章节和关联图片的路径。"
        "参数 query 是检索关键词或问题。"
        "如果要查询某个章节的所有内容，使用另一个工具 get_section_images。"
    )

    db: Any = None
    config: Any = None

    def __init__(self, db: Neo4jVector, config: Config) -> None:
        super().__init__(db=db, config=config)

    def _run(self, query: str) -> str:
        results = self.db.similarity_search_with_score(query, k=self.config.search_k)

        if not results:
            return "未找到相关结果，请尝试不同的关键词。"

        output_parts: list[str] = []
        for i, (doc, score) in enumerate(results, 1):
            sec = doc.metadata.get("section", "")
            section = [f"--- 结果 {i} (相似度: {score:.4f}) [章节: {sec}] ---"]
            section.append(f"文本内容:\n{doc.page_content}")

            image_descs: list[str] = json.loads(doc.metadata.get("image_descriptions", "[]"))
            image_paths: list[str] = json.loads(doc.metadata.get("image_paths", "[]"))

            if image_descs:
                section.append("\n相关图片描述:")
                for j, desc in enumerate(image_descs):
                    section.append(f"  图{j + 1}: {desc}")

            if image_paths:
                section.append("\n相关图片:")
                for j, path in enumerate(image_paths):
                    desc = image_descs[j] if j < len(image_descs) else ""
                    section.append(f"  {_image_to_html(self.config, path, alt=desc)}")

            output_parts.append("\n".join(section))

        return "\n\n".join(output_parts)


# ── GetSectionImages ────────────────────────────────────────────────────────


class GetSectionImages(BaseTool):
    """Retrieve all text and images for a named document section."""

    name: str = "get_section_images"
    description: str = (
        "获取指定章节的所有文本内容和图片路径。"
        "参数 section_name 是章节名称，如'客户管理'、'账单管理'等。"
        "返回该章节的所有文本段落和关联图片。"
    )

    db: Any = None
    config: Any = None

    def __init__(self, db: Neo4jVector, config: Config) -> None:
        super().__init__(db=db, config=config)

    def _run(self, section_name: str) -> str:
        records = self._query_neo4j(
            """
            MATCH (n)
            WHERE n.source = 'billing_manual'
              AND toLower(n.section) CONTAINS toLower($section)
            RETURN n.text          AS text,
                   n.image_descriptions AS image_descs,
                   n.image_paths   AS image_paths,
                   n.section       AS section
            ORDER BY n.chunk_index
            """,
            {"section": section_name},
        )

        if not records:
            sections = self._query_neo4j(
                """
                MATCH (n)
                WHERE n.source = 'billing_manual' AND n.section IS NOT NULL
                RETURN DISTINCT n.section AS section
                ORDER BY n.chunk_index
                """,
                {},
            )
            section_names = [r["section"] for r in sections]
            if section_names:
                return (
                    f"未找到章节 '{section_name}'。可用章节:\n"
                    + "\n".join(f"- {s}" for s in section_names)
                )
            return f"未找到章节 '{section_name}'。"

        output = [f"## 章节: {records[0].get('section', '未知')}"]
        all_images: set[str] = set()

        for rec in records:
            text = rec.get("text", "")
            if text:
                output.append(text[:500])
            img_paths: list[str] = json.loads(rec.get("image_paths", "[]") or "[]")
            all_images.update(img_paths)

        if all_images:
            output.append(f"\n### 图片 ({len(all_images)} 张)")
            for path in sorted(all_images):
                output.append(
                    _image_to_html(self.config, path, alt=os.path.basename(path))
                )

        return "\n\n".join(output)

    # ── private helper (deduplicates the GraphDatabase.driver pattern) ───────

    def _query_neo4j(self, cypher: str, params: dict) -> list:
        """Execute a Cypher query and return the result records as a list of dicts."""
        try:
            driver = GraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_username, self.config.neo4j_password),
            )
            with driver.session(database=self.config.neo4j_database) as session:
                result = session.run(cypher, **params)
                records = list(result)
            driver.close()
            return records
        except Exception as exc:
            raise VectorStoreError(f"Neo4j query failed: {exc}") from exc

# [AGC:END]
