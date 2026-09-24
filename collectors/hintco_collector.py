"""Modular Hintco collector."""

from __future__ import annotations

from typing import Any

from config import HINTCO_SOURCES

from collectors.base_collector import BaseCollector
from collectors.shared_engine import run_sources


class HintcoCollector(BaseCollector):
    """Collect intelligence from selected Hintco pages."""

    collector_id = "hintco"
    collector_name = "Hintco"
    enabled = True

    @property
    def sources(self) -> list[dict]:
        """Return the configured Hintco sources."""

        return [
            {
                **source,
                "enabled": source.get("enabled", True),
            }
            for source in HINTCO_SOURCES
        ]

    def run(
        self,
        selected_source_ids: list[str] | None = None,
    ) -> list[Any]:
        """Run all enabled Hintco sources or only selected sources."""

        is_valid, validation_message = self.validate_configuration()

        if not is_valid:
            raise ValueError(
                f"{self.collector_name} configuration error: "
                f"{validation_message}"
            )

        sources_to_run = self.get_selected_sources(
            selected_source_ids
        )

        return run_sources(sources_to_run)