# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual.models
=====================
Data containers for parsed document elements.

This module has zero internal dependencies.
"""

from dataclasses import dataclass

# [AGC:START] tool=Cc author=fangkun


@dataclass
class TextElement:
    """A text paragraph extracted from a .docx document."""

    type: str = "text"
    content: str = ""
    section: str = ""       # Heading the paragraph belongs to
    is_heading: bool = False


@dataclass
class ImageElement:
    """An image extracted from a .docx document."""

    type: str = "image"
    path: str = ""                        # Saved image file path
    nearest_paragraph_text: str = ""      # Closest surrounding paragraph text
    image_description: str = ""           # Filled in by ImageDescriber
    section: str = ""                     # Heading the image belongs to

# [AGC:END]
