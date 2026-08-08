# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual.exceptions
=========================
Custom exception hierarchy for the billing_manual package.

This module has zero internal dependencies so any submodule can import
from it without circular-import risk.
"""

# [AGC:START] tool=Cc author=fangkun


class BillingManualError(Exception):
    """Base exception for all billing_manual errors."""


class DocumentParseError(BillingManualError):
    """Raised when .docx parsing fails (corrupt file, missing images, etc.)."""


class ImageDescribeError(BillingManualError):
    """Raised when the VL model fails to describe an image."""


class VectorStoreError(BillingManualError):
    """Raised when Neo4j vector store creation or query fails."""

# [AGC:END]
