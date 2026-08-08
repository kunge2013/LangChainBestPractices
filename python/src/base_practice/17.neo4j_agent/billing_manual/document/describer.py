# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual.document.describer
==================================
Call a VL (Vision-Language) model to generate Chinese descriptions for images.

Adapted from 3.billing_manual_agent.py :: ImageDescriber.
"""

import base64
import logging
import os
import time

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from ..config import Config
from ..exceptions import ImageDescribeError
from ..models import ImageElement

logger = logging.getLogger(__name__)

# [AGC:START] tool=Cc author=fangkun


class ImageDescriber:
    """Generate Chinese image descriptions using a Vision-Language model."""

    PROMPT: str = (
        "请用中文详细描述这张图片的内容，包括图片中的文字、界面元素、操作流程、步骤等。"
        "描述要准确完整，以便后续用于知识检索。"
    )

    def __init__(self, config: Config) -> None:
        self.config = config
        self.model = ChatOpenAI(**config.get_llm_params())

    def describe_batch(
        self,
        images: list[ImageElement],
        max_retries: int | None = None,
    ) -> list[ImageElement]:
        """Describe each image in *images*, filling image_description in place."""
        max_retries = max_retries or self.config.describe_max_retries
        total = len(images)

        for i, img in enumerate(images, 1):
            if not img.path or not os.path.exists(img.path):
                logger.warning("Image not found, skipping: %s", img.path)
                continue

            for attempt in range(1, max_retries + 1):
                try:
                    logger.info("Describing image %d/%d (attempt %d/%d)", i, total, attempt, max_retries)
                    img.image_description = self._describe_one(img.path)
                    logger.info("Description OK: %s...", img.image_description[:50])
                    break
                except Exception as exc:
                    logger.warning("Description failed (attempt %d/%d): %s", attempt, max_retries, exc)
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
            else:
                img.image_description = "描述生成失败"

        done = sum(1 for img in images if img.image_description)
        logger.info("Image descriptions complete: %d/%d", done, total)
        return images

    def _describe_one(self, image_path: str) -> str:
        with open(image_path, "rb") as fh:
            image_b64 = base64.b64encode(fh.read()).decode("utf-8")

        message = HumanMessage(
            content=[
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                {"type": "text", "text": self.PROMPT},
            ]
        )

        try:
            response = self.model.invoke([message], max_tokens=self.config.describe_image_max_tokens)
        except Exception as exc:
            raise ImageDescribeError(f"VL model call failed for '{image_path}'") from exc

        content = response.content
        return content.strip() if content else "图片描述生成失败"

# [AGC:END]
