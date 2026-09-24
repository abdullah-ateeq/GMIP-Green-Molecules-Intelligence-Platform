from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PageResult:
    source_id: str
    source_name: str
    source_url: str
    source_type: str

    page_title: str
    extracted_text: str
    content_hash: str

    products: list[str] = field(default_factory=list)
    event_types: list[str] = field(default_factory=list)

    is_relevant: bool = False
    downloaded_at: datetime | None = None


@dataclass
class CollectionResult:
    source_id: str
    source_name: str
    source_url: str
    status: str

    relevant: bool
    products: list[str] = field(default_factory=list)
    event_types: list[str] = field(default_factory=list)

    message: str = ""
    error: str | None = None