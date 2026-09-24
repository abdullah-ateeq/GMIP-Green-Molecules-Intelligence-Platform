"""Common interface for all GMIP market intelligence collectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
    """Base class for every GMIP market intelligence collector."""

    collector_id: str = ""
    collector_name: str = ""
    enabled: bool = True

    @property
    @abstractmethod
    def sources(self) -> list[dict]:
        """Return all source definitions belonging to the collector."""
        raise NotImplementedError

    @property
    def source_count(self) -> int:
        """Return the total number of configured sources."""
        return len(self.sources)

    def get_enabled_sources(self) -> list[dict]:
        """Return sources enabled in the collector configuration."""
        return [
            source
            for source in self.sources
            if source.get("enabled", True)
        ]

    def get_selected_sources(
        self,
        selected_source_ids: list[str] | None = None,
    ) -> list[dict]:
        """
        Return enabled sources matching an optional user selection.

        If no source IDs are supplied, every enabled source is returned.
        """
        enabled_sources = self.get_enabled_sources()

        if selected_source_ids is None:
            return enabled_sources

        selected_ids = set(selected_source_ids)

        return [
            source
            for source in enabled_sources
            if source["source_id"] in selected_ids
        ]

    @abstractmethod
    def run(
        self,
        selected_source_ids: list[str] | None = None,
    ) -> list[Any]:
        """Run all enabled sources or only the selected sources."""
        raise NotImplementedError

    def validate_configuration(self) -> tuple[bool, str]:
        """Validate the collector and its source definitions."""

        if not self.collector_id.strip():
            return False, "Collector ID is missing."

        if not self.collector_name.strip():
            return False, "Collector name is missing."

        if self.source_count < 1:
            return False, "Collector has no configured sources."

        source_ids = [
            source.get("source_id")
            for source in self.sources
        ]

        if any(not source_id for source_id in source_ids):
            return False, "One or more sources have no source ID."

        if len(source_ids) != len(set(source_ids)):
            return False, "Duplicate source IDs were detected."

        return True, "Collector configuration is valid."

    def get_status(self) -> dict[str, Any]:
        """Return collector-level metadata."""

        is_valid, validation_message = self.validate_configuration()

        return {
            "collector_id": self.collector_id,
            "collector_name": self.collector_name,
            "enabled": self.enabled,
            "source_count": self.source_count,
            "enabled_source_count": len(self.get_enabled_sources()),
            "configuration_valid": is_valid,
            "validation_message": validation_message,
        }

    def get_source_statuses(self) -> list[dict[str, Any]]:
        """Return metadata for every selectable source."""

        return [
            {
                "collector_id": self.collector_id,
                "collector_name": self.collector_name,
                "source_id": source["source_id"],
                "source_name": source["source_name"],
                "source_url": source["url"],
                "source_type": source.get("source_type", ""),
                "enabled": source.get("enabled", True),
            }
            for source in self.sources
        ]