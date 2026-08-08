# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual.document.parser
===============================
Parse .docx files, extracting text paragraphs and images in document order.

Adapted from 3.billing_manual_agent.py :: DocxParser.
"""

import io
import logging
import os
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from PIL import Image

from ..config import Config
from ..exceptions import DocumentParseError
from ..models import ImageElement, TextElement

logger = logging.getLogger(__name__)

# [AGC:START] tool=Cc author=fangkun


class DocxParser:
    """Parse a .docx file into an ordered list of TextElement / ImageElement."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def parse(self, docx_path: str) -> list[TextElement | ImageElement]:
        """Parse *docx_path* and return an ordered list of document elements."""
        try:
            Path(self.config.images_output_dir).mkdir(parents=True, exist_ok=True)

            doc = Document(docx_path)
            elements: list[TextElement | ImageElement] = []
            image_counter = 0
            seen_rids: set[str] = set()
            current_section = "前言"

            for para in doc.paragraphs:
                text = para.text.strip()
                style_name = (para.style.name or "").lower()
                is_heading = "heading" in style_name or "title" in style_name

                if is_heading and text:
                    current_section = text

                if text:
                    elements.append(
                        TextElement(content=text, section=current_section, is_heading=is_heading)
                    )

                for run in para.runs:
                    for image_bytes, image_ext in self._extract_images_from_run(run, doc, seen_rids):
                        image_path = os.path.join(
                            self.config.images_output_dir,
                            f"img_{image_counter}.{image_ext}",
                        )
                        try:
                            img = Image.open(io.BytesIO(image_bytes))
                            img.save(image_path, "PNG")
                            elements.append(
                                ImageElement(
                                    path=image_path,
                                    nearest_paragraph_text=text if text else self._last_text(elements),
                                    section=current_section,
                                )
                            )
                            image_counter += 1
                            logger.info("Extracted image %d: %s [%s]", image_counter, image_path, current_section)
                        except Exception as exc:
                            logger.warning("Failed to save image: %s", exc)

            for shape in doc.inline_shapes:
                image_bytes = self._extract_image_bytes(shape, seen_rids)
                if image_bytes is None:
                    continue
                image_path = os.path.join(self.config.images_output_dir, f"img_{image_counter}.png")
                try:
                    img = Image.open(io.BytesIO(image_bytes))
                    img.save(image_path, "PNG")
                    elements.append(
                        ImageElement(
                            path=image_path,
                            nearest_paragraph_text=self._last_text(elements),
                            section=current_section,
                        )
                    )
                    image_counter += 1
                    logger.info("Extracted image %d (inline_shape): %s", image_counter, image_path)
                except Exception as exc:
                    logger.warning("Failed to save image: %s", exc)

            for rel in doc.part.rels.values():
                if "image" not in rel.reltype or rel.rId in seen_rids:
                    continue
                try:
                    blob = rel.target_part.blob
                    ext = rel.target_part.content_type.split("/")[-1].split("+")[0] or "png"
                    image_path = os.path.join(self.config.images_output_dir, f"img_{image_counter}.{ext}")
                    img = Image.open(io.BytesIO(blob))
                    img.save(image_path, "PNG")
                    elements.append(
                        ImageElement(
                            path=image_path,
                            nearest_paragraph_text=self._last_text(elements),
                            section=current_section,
                        )
                    )
                    image_counter += 1
                    logger.info("Extracted image %d (fallback): %s", image_counter, image_path)
                except Exception as exc:
                    logger.debug("Fallback image extraction failed: %s", exc)

            text_count = sum(1 for e in elements if isinstance(e, TextElement))
            image_count = sum(1 for e in elements if isinstance(e, ImageElement))
            logger.info("Document parsed: %d text paragraphs, %d images", text_count, image_count)
            return elements

        except DocumentParseError:
            raise
        except Exception as exc:
            raise DocumentParseError(f"Failed to parse '{docx_path}'") from exc

    @staticmethod
    def _last_text(elements: list) -> str:
        for elem in reversed(elements):
            if isinstance(elem, TextElement) and elem.content:
                return elem.content
        return ""

    @staticmethod
    def _extract_images_from_run(run, doc, seen_rids: set) -> list[tuple[bytes, str]]:
        images: list[tuple[bytes, str]] = []
        nsmap = {
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }
        for blip in run._element.findall(".//a:blip", namespaces=nsmap):
            rid = blip.get(qn("r:embed")) or blip.get(qn("r:link"))
            if not rid or rid in seen_rids:
                continue
            try:
                image_part = doc.part.related_parts.get(rid)
                if image_part:
                    seen_rids.add(rid)
                    blob = image_part.blob
                    ext = image_part.content_type.split("/")[-1].split("+")[0] or "png"
                    images.append((blob, ext))
            except Exception as exc:
                logger.debug("Failed to extract image from run (rid=%s): %s", rid, exc)
        return images

    @staticmethod
    def _extract_image_bytes(shape, seen_rids: set) -> bytes | None:
        try:
            nsmap = {
                "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
                "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
                "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
            }
            r_ids = shape._element.findall(
                "pic:pic/pic:blipFill/a:blip/@r:embed", namespaces=nsmap
            )
            if not r_ids:
                return None
            r_id = r_ids[0]
            if r_id in seen_rids:
                return None
            seen_rids.add(r_id)
            image_part = shape.part.related_parts.get(r_id)
            return image_part.blob if image_part else None
        except Exception as exc:
            logger.debug("inline_shape image extraction failed: %s", exc)
            return None

# [AGC:END]
