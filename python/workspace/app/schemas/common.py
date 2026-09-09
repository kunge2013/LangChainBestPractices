"""
Common Pydantic schemas shared across modules.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    total: int = 0
    list: List[T] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class ApiResponse(BaseModel, Generic[T]):
    """Unified API response wrapper."""
    code: str = "0"
    message: str = "成功"
    data: Optional[T] = None
    timestamp: Optional[int] = None


class PageQuery(BaseModel):
    """Base pagination query parameters."""
    pageNum: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=1000)

    @property
    def offset(self) -> int:
        return (self.pageNum - 1) * self.pageSize
