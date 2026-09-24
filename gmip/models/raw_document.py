from __future__ import annotations

import hashlib
import json
import uuid

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class RawDocument:
    """
    Standard raw document collected from an external source.

    RawDocument represents collected source material before it is interpreted
    by a source-specific parser.
    """

    source_id: str
    source_name: str
    source_url: str

    document_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    title: str | None = None
    html: str | None = None
    text: str | None = None

    status: str = "SUCCESS"
    content_type: str = "text/html"
    language: str = "en"

    published_at: datetime | None = None
    collected_at: datetime = field(default_factory=utc_now)

    collector_id: str | None = None
    collector_name: str | None = None

    http_status_code: int | None = None
    response_time_seconds: float | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    error: str | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        self.source_id = self.source_id.strip()
        self.source_name = self.source_name.strip()
        self.source_url = self.source_url.strip()

        self.title = self._clean_optional_text(self.title)
        self.html = self._clean_optional_content(self.html)
        self.text = self._clean_optional_content(self.text)
        self.error = self._clean_optional_text(self.error)

        self.status = self.status.strip().upper() or "UNKNOWN"
        self.content_type = (
            self.content_type.strip().lower()
            or "application/octet-stream"
        )
        self.language = self.language.strip().lower() or "en"

        if not self.source_id:
            raise ValueError("RawDocument source_id cannot be empty.")

        if not self.source_name:
            raise ValueError("RawDocument source_name cannot be empty.")

        if not self.source_url.startswith(
            (
                "http://",
                "https://",
            )
        ):
            raise ValueError(
                "RawDocument source_url must begin with "
                "http:// or https://."
            )

        if (
            self.http_status_code is not None
            and not 100 <= self.http_status_code <= 599
        ):
            raise ValueError(
                "HTTP status code must be between 100 and 599."
            )

        if (
            self.response_time_seconds is not None
            and self.response_time_seconds < 0
        ):
            raise ValueError(
                "Response time cannot be negative."
            )

        if self.content_hash is None:
            self.content_hash = self.generate_content_hash()

    @staticmethod
    def _clean_optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        cleaned = " ".join(str(value).split())
        return cleaned or None

    @staticmethod
    def _clean_optional_content(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    @property
    def has_content(self) -> bool:
        """Return True when HTML or extracted text is available."""
        return bool(self.html or self.text)

    @property
    def is_successful(self) -> bool:
        """Return True when the collection status represents success."""
        return self.status in {
            "SUCCESS",
            "OK",
            "RELEVANT",
            "NOT_RELEVANT",
        }

    @property
    def is_error(self) -> bool:
        """Return True when collection failed."""
        return not self.is_successful

    def generate_content_hash(self) -> str:
        """
        Generate a stable SHA-256 hash for collected content.

        Operational fields such as document_id and collected_at are excluded,
        so collecting identical content again produces the same hash.
        """
        hash_payload = {
            "source_id": self.source_id,
            "source_url": self.source_url,
            "title": self.title,
            "html": self.html,
            "text": self.text,
            "content_type": self.content_type,
            "language": self.language,
        }

        serialized = json.dumps(
            hash_payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    def refresh_content_hash(self) -> str:
        """Regenerate and return the content hash."""
        self.content_hash = self.generate_content_hash()
        return self.content_hash

    def to_dict(self) -> dict[str, Any]:
        """Convert the raw document into a serializable dictionary."""
        result = asdict(self)
        result["collected_at"] = self.collected_at.isoformat()
        result["published_at"] = (
            self.published_at.isoformat() if self.published_at else None
        )
        result["has_content"] = self.has_content
        result["is_successful"] = self.is_successful
        result["is_error"] = self.is_error

        return result

    def to_json(
        self,
        indent: int = 2,
    ) -> str:
        """Serialize the raw document to formatted JSON."""
        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=False,
            default=str,
        )

    def save_json(
        self,
        file_path: str,
    ) -> None:
        """Save the raw document as JSON."""
        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(self.to_json())