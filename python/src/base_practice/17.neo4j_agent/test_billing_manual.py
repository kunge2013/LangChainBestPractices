# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
Unit tests for the billing_manual package.

Tests cover:
- exceptions module (hierarchy)
- models module (dataclass defaults)
- config module (helper methods)
- knowledge.tools._image_to_html
- knowledge.vectorstore.VectorStoreBuilder._find_nearby_images
- knowledge.tools.KnowledgeSearcher._run  (mocked db)
- knowledge.tools.GetSectionImages._query_neo4j  (mocked neo4j driver)
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the package is importable when running from the 17.neo4j_agent dir
sys.path.insert(0, str(Path(__file__).resolve().parent))

# [AGC:START] tool=Cc author=fangkun


# ── exceptions ──────────────────────────────────────────────────────────────


class TestExceptions:
    def test_hierarchy(self):
        from billing_manual.exceptions import (
            BillingManualError,
            DocumentParseError,
            ImageDescribeError,
            VectorStoreError,
        )

        assert issubclass(DocumentParseError, BillingManualError)
        assert issubclass(ImageDescribeError, BillingManualError)
        assert issubclass(VectorStoreError, BillingManualError)

    def test_raise_and_catch(self):
        from billing_manual.exceptions import DocumentParseError, BillingManualError

        with pytest.raises(BillingManualError):
            raise DocumentParseError("boom")


# ── models ──────────────────────────────────────────────────────────────────


class TestModels:
    def test_text_element_defaults(self):
        from billing_manual.models import TextElement

        t = TextElement()
        assert t.type == "text"
        assert t.content == ""
        assert t.is_heading is False

    def test_image_element_defaults(self):
        from billing_manual.models import ImageElement

        img = ImageElement(path="/tmp/img.png")
        assert img.type == "image"
        assert img.image_description == ""


# ── config ──────────────────────────────────────────────────────────────────


class TestConfig:
    def test_get_neo4j_params_keys(self):
        from billing_manual.config import Config

        c = Config()
        params = c.get_neo4j_params()
        assert set(params.keys()) == {"url", "username", "password", "database"}

    def test_get_llm_params_keys(self):
        from billing_manual.config import Config

        c = Config()
        params = c.get_llm_params()
        assert set(params.keys()) == {"model", "base_url", "api_key", "temperature", "max_tokens"}


# ── _image_to_html ──────────────────────────────────────────────────────────


class TestImageToHtml:
    def test_returns_empty_for_missing_file(self, tmp_path):
        from billing_manual.config import Config
        from billing_manual.knowledge.tools import _image_to_html

        c = Config()
        result = _image_to_html(c, str(tmp_path / "nonexistent.png"))
        assert result == ""

    def test_returns_img_tag_for_existing_file(self, tmp_path):
        from billing_manual.config import Config
        from billing_manual.knowledge.tools import _image_to_html

        img_file = tmp_path / "img_0.png"
        img_file.write_bytes(b"fake-png")

        c = Config(image_base_url="http://localhost:9999")
        result = _image_to_html(c, str(img_file), alt="test")
        assert 'src="http://localhost:9999/img_0.png"' in result
        assert 'alt="test"' in result


# ── VectorStoreBuilder._find_nearby_images ──────────────────────────────────


class TestFindNearbyImages:
    def test_returns_images_between_text_elements(self):
        from billing_manual.knowledge.vectorstore import VectorStoreBuilder
        from billing_manual.models import ImageElement, TextElement

        t1 = TextElement(content="before")
        img1 = ImageElement(path="a.png")
        img2 = ImageElement(path="b.png")
        t2 = TextElement(content="after")

        result = VectorStoreBuilder._find_nearby_images(t1, [t1, img1, img2, t2])
        assert result == [img1, img2]

    def test_returns_empty_when_no_nearby_images(self):
        from billing_manual.knowledge.vectorstore import VectorStoreBuilder
        from billing_manual.models import TextElement

        t1 = TextElement(content="a")
        t2 = TextElement(content="b")

        result = VectorStoreBuilder._find_nearby_images(t1, [t1, t2])
        assert result == []


# ── KnowledgeSearcher._run ──────────────────────────────────────────────────


class TestKnowledgeSearcher:
    def test_returns_not_found_when_empty(self):
        from billing_manual.config import Config
        from billing_manual.knowledge.tools import KnowledgeSearcher

        mock_db = MagicMock()
        mock_db.similarity_search_with_score.return_value = []
        c = Config()

        searcher = KnowledgeSearcher(mock_db, c)
        result = searcher._run("anything")
        assert "未找到" in result

    def test_returns_formatted_results(self, tmp_path):
        from langchain_core.documents import Document as LC_Doc

        from billing_manual.config import Config
        from billing_manual.knowledge.tools import KnowledgeSearcher

        # Create a fake image file so _image_to_html returns a tag
        img_file = tmp_path / "img_0.png"
        img_file.write_bytes(b"fake")

        mock_doc = LC_Doc(
            page_content="How to create a customer",
            metadata={
                "section": "客户管理",
                "image_descriptions": json.dumps(["Screenshot of form"], ensure_ascii=False),
                "image_paths": json.dumps([str(img_file)], ensure_ascii=False),
            },
        )
        mock_db = MagicMock()
        mock_db.similarity_search_with_score.return_value = [(mock_doc, 0.95)]

        c = Config(image_base_url="http://localhost:2024")
        searcher = KnowledgeSearcher(mock_db, c)
        result = searcher._run("create customer")

        assert "0.9500" in result
        assert "客户管理" in result
        assert "How to create a customer" in result
        assert "Screenshot of form" in result


# ── GetSectionImages._query_neo4j ───────────────────────────────────────────


class TestGetSectionImages:
    def test_query_neo4j_returns_records(self):
        from billing_manual.config import Config
        from billing_manual.knowledge.tools import GetSectionImages

        mock_session = MagicMock()
        mock_session.run.return_value = [{"section": "客户管理", "text": "hello"}]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        c = Config()

        with patch("billing_manual.knowledge.tools.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver
            tool = GetSectionImages(db=MagicMock(), config=c)
            records = tool._query_neo4j("MATCH (n) RETURN n", {})

        assert len(records) == 1
        assert records[0]["section"] == "客户管理"

    def test_query_neo4j_raises_vector_store_error_on_failure(self):
        from billing_manual.config import Config
        from billing_manual.exceptions import VectorStoreError
        from billing_manual.knowledge.tools import GetSectionImages

        mock_driver = MagicMock()
        mock_driver.session.side_effect = RuntimeError("connection refused")

        c = Config()

        with patch("billing_manual.knowledge.tools.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = mock_driver
            tool = GetSectionImages(db=MagicMock(), config=c)

            with pytest.raises(VectorStoreError, match="Neo4j query failed"):
                tool._query_neo4j("MATCH (n) RETURN n", {})


# ── Public API smoke test ──────────────────────────────────────────────────


class TestPublicApi:
    def test_all_exports_importable(self):
        import billing_manual

        expected = {
            "Config", "TextElement", "ImageElement",
            "BillingManualError", "DocumentParseError", "ImageDescribeError", "VectorStoreError",
            "DocxParser", "ImageDescriber",
            "VectorStoreBuilder", "KnowledgeSearcher", "GetSectionImages",
            "BillingAgent", "BillingManualPipeline", "build_agent",
        }
        assert expected.issubset(set(billing_manual.__all__))

# [AGC:END]
