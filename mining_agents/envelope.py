"""The one SOP tool envelope. Every tool in this build returns this shape."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ToolError(BaseModel):
    """RFC 7807 in the SOP's shape."""
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class Meta(BaseModel):
    timestamp: str
    tables_read: list[str]
    rows_scanned: int = 0


class Envelope(BaseModel):
    success: bool
    data: dict = Field(default_factory=dict)
    error: ToolError | None = None
    meta: Meta


def ok(data: dict, tables_read: list[str], rows_scanned: int = 0) -> dict:
    return Envelope(
        success=True, data=data, error=None,
        meta=Meta(timestamp=_now(), tables_read=list(tables_read),
                  rows_scanned=rows_scanned),
    ).model_dump()


def fail(code: str, message: str, details: dict, tables_read: list[str]) -> dict:
    return Envelope(
        success=False, data={},
        error=ToolError(code=code, message=message, details=details),
        meta=Meta(timestamp=_now(), tables_read=list(tables_read), rows_scanned=0),
    ).model_dump()
