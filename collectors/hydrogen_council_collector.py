"""Hydrogen Council market intelligence collector."""

from __future__ import annotations

from typing import Any

from config import HYDROGEN_COUNCIL_SOURCES

from collectors.base_collector import BaseCollector
from collectors.shared_engine import run_sources


class HydrogenCouncilCollector(BaseCollector):
    """Hydrogen Council collector."""

    collector_id = "hydrogen_council"
    collector_name = "Hydrogen Council"
    enabled = True

    @property
    def sources(self) -> list[dict]:
        return [
            {
                **source,
                "enabled": source.get("enabled", True),
            }
            for source in HYDROGEN_COUNCIL_SOURCES
        ]

    def run(
        self,
        selected_source_ids: list[str] | None = None,
    ) -> list[Any]:

        valid, message = self.validate_configuration()

        if not valid:
            raise ValueError(message)

        return run_sources(
            self.get_selected_sources(selected_source_ids)
        )