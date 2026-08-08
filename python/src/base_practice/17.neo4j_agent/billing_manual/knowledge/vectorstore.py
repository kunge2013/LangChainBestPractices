# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual.knowledge.vectorstore
=====================================
Build LangChain Documents from parsed elements and persist to a Neo4j vector store.

Adapted from 3.billing_manual_agent.py :: VectorStoreBuilder.
"""

import json
import logging

from langchain_core.documents import Document as LangchainDocument
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import Config
from ..exceptions import VectorStoreError
from ..models import ImageElement, TextElement

logger = logging.getLogger(__name__)

# [AGC:START] tool=Cc author=fangkun


class VectorStoreBuilder:
    """Build LangChain Documents and write them to a Neo4j vector index."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.embedding_model,
            model_kwargs={"device": config.embedding_device},
            encode_kwargs={"normalize_embeddings": True},
            cache_folder=config.embedding_cache_dir,
        )

    # ── public API ──────────────────────────────────────────────────────────

    def build_documents(
        self, elements: list[TextElement | ImageElement]
    ) -> list[LangchainDocument]:
        """Convert parsed elements into LangChain Documents with metadata."""
        docs: list[LangchainDocument] = []
        chunk_index = 0

        for elem in elements:
            if not isinstance(elem, TextElement):
                continue

            nearby_images = self._find_nearby_images(elem, elements)
            metadata = {
                "source": "billing_manual",
                "section": elem.section,
                "chunk_index": chunk_index,
                "image_descriptions": json.dumps(
                    [img.image_description for img in nearby_images], ensure_ascii=False
                ),
                "image_paths": json.dumps(
                    [img.path for img in nearby_images], ensure_ascii=False
                ),
            }
            docs.append(LangchainDocument(page_content=elem.content, metadata=metadata))
            chunk_index += 1

        return docs

    def build(
        self, docs: list[LangchainDocument], force_recreate: bool = False
    ) -> Neo4jVector:
        """Create a new Neo4j vector index or load the existing one."""
        try:
            if not force_recreate:
                try:
                    db = Neo4jVector.from_existing_index(
                        embedding=self.embeddings,
                        index_name=self.config.vector_index_name,
                        text_node_property="text",
                        embedding_node_property="embedding",
                        **self.config.get_neo4j_params(),
                    )
                    logger.info("Loaded existing vector index")
                    return db
                except Exception as exc:
                    logger.warning("Failed to load existing index: %s", exc)
                    raise VectorStoreError(
                        "Vector index does not exist. "
                        "Run pipeline.build(force_recreate=True) to initialise."
                    ) from exc

            if not docs:
                raise ValueError("docs must be non-empty when force_recreate=True")

            logger.info("Creating vector index with %d documents...", len(docs))
            db = Neo4jVector.from_documents(
                documents=docs,
                embedding=self.embeddings,
                index_name=self.config.vector_index_name,
                text_node_property="text",
                embedding_node_property="embedding",
                **self.config.get_neo4j_params(),
            )
            logger.info("Vector index created")
            return db

        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"Vector store operation failed: {exc}") from exc

    # ── private helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _find_nearby_images(text_elem: TextElement, elements: list) -> list[ImageElement]:
        """Return all ImageElements that appear immediately after *text_elem*."""
        images: list[ImageElement] = []
        found = False
        for elem in elements:
            if elem is text_elem:
                found = True
                continue
            if found:
                if isinstance(elem, ImageElement):
                    images.append(elem)
                elif isinstance(elem, TextElement):
                    break
        return images

# [AGC:END]
