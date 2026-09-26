"""
Legacy-compatible H2 View collector (RSS-only).

Adapts the new-architecture gmip.collectors.h2_view_collector.H2ViewCollector
(which already implements the real RSS fetch via feedparser) to the legacy
BaseCollector contract, so CollectorManager can run it alongside Hintco and
Hydrogen Council without changing either existing interface.

This file intentionally contains no HTML scraping, no article-page
downloading, and no duplicated source configuration — the feed URL comes
from the single SourceDefinition in gmip.config.SOURCE_REGISTRY.
"""
from __future__ import annotations

from typing import Any

from collectors.base_collector import BaseCollector
from gmip.collectors.h2_view_collector import (
    H2ViewCollector as GmipH2ViewCollector,
)
from gmip.config import get_source_definition
from hintco_collector import parse_and_persist_intelligence
from models import CollectionResult


class H2ViewCollector(BaseCollector):
    """Legacy-contract wrapper around the RSS-based H2 View collector."""

    collector_id = "h2_view"
    collector_name = "H2 View"
    enabled = True

    @property
    def sources(self) -> list[dict]:
        """Return the single H2 View source, from SOURCE_REGISTRY."""

        source_definition = get_source_definition("h2_view")

        if source_definition is None:
            return []

        return [
            {
                "source_id": source_definition.source_id,
                "source_name": source_definition.source_name,
                "url": source_definition.feed_url
                or source_definition.base_url
                or "",
                "source_type": source_definition.source_category.value,
                "enabled": source_definition.enabled,
            }
        ]

    def run(
        self,
        selected_source_ids: list[str] | None = None,
    ) -> list[Any]:
        """Run the H2 View RSS collection, or a no-op if not selected."""

        is_valid, validation_message = self.validate_configuration()

        if not is_valid:
            raise ValueError(
                f"{self.collector_name} configuration error: "
                f"{validation_message}"
            )

        sources_to_run = self.get_selected_sources(selected_source_ids)

        if not sources_to_run:
            return []

        return [self._collect_and_persist()]

    def _collect_and_persist(self) -> CollectionResult:
        source_definition = get_source_definition("h2_view")
        feed_url = source_definition.feed_url or source_definition.base_url or ""

        try:
            raw_documents = GmipH2ViewCollector(source_definition).collect()

        except Exception as exc:
            return CollectionResult(
                source_id=self.collector_id,
                source_name=self.collector_name,
                source_url=feed_url,
                status="FEED_ERROR",
                relevant=False,
                products=[],
                event_types=[],
                message="Failed to collect the H2 View RSS feed.",
                error=str(exc),
            )

        if not raw_documents:
            return CollectionResult(
                source_id=self.collector_id,
                source_name=self.collector_name,
                source_url=feed_url,
                status="NO_ITEMS",
                relevant=False,
                products=[],
                event_types=[],
                message="No items found in the H2 View RSS feed.",
            )

        new_count = 0
        updated_count = 0
        unchanged_count = 0

        for raw_document in raw_documents:
            # Persists the RawDocument, parses it via the shared
            # ParserRegistry (H2ViewParser), and persists resulting
            # IntelligenceObjects with NEW/UPDATED/UNCHANGED detection.
            summary = parse_and_persist_intelligence(raw_document)
            new_count += summary["new"]
            updated_count += summary["updated"]
            unchanged_count += summary["unchanged"]

        return CollectionResult(
            source_id=self.collector_id,
            source_name=self.collector_name,
            source_url=feed_url,
            status="SUCCESS",
            relevant=new_count > 0 or updated_count > 0,
            products=[],
            event_types=[],
            message=(
                f"Collected {len(raw_documents)} item(s) from H2 View "
                f"({new_count} new, {updated_count} updated, "
                f"{unchanged_count} unchanged)."
            ),
        )
