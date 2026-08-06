"""Common response schemas."""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Message(BaseModel):
    message: str


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    result: Optional[Any] = None
