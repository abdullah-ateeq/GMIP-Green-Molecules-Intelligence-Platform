from __future__ import annotations

import logging

from abc import ABC, abstractmethod
from typing import Any

from gmip.config.source_definition import SourceDefinition
from gmip.models.raw_document import RawDocument


class GmipCollector(ABC):
    """
    Common interface for new-architecture GMIP collectors.

    Distinct from the legacy collectors.base_collector.BaseCollector (which
    is tied to the old CollectionResult/dict-source shape used by Hintco and
    Hydrogen Council). A GmipCollector's only job is retrieving content and
    producing RawDocuments — classification and structuring belong to a
    BaseParser, not here.
    """

    collector_id: str = ""
    collector_name: str = ""

    def __init__(
        self,
        source_definition: SourceDefinition,
        logger: logging.Logger | None = None,
    ) -> None:
        self.source_definition = source_definition
        self.logger = logger or logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

    @abstractmethod
    def collect(self) -> list[RawDocument]:
        """
        Retrieve content for this source and return RawDocuments.

        Must not raise on ordinary failure (unreachable feed, missing
        credentials, etc.) — return an empty list and let the caller record
        the failure via source health tracking instead.
        """

    def get_status(self) -> dict[str, Any]:
        """Return collector-level metadata for source health reporting."""
        source = self.source_definition

        return {
            "collector_id": self.collector_id,
            "collector_name": self.collector_name,
            "source_id": source.source_id,
            "access_mode": source.access_mode.value,
            "enabled": source.enabled,
            "requires_auth": source.requires_auth,
            "license_required": source.license_required,
            "is_active": source.is_active,
        }
