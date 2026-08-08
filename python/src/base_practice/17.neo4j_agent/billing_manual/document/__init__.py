# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""billing_manual.document - document processing subdomain."""

from .describer import ImageDescriber
from .parser import DocxParser

__all__ = ["DocxParser", "ImageDescriber"]
