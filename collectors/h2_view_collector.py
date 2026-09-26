"""H2 View market intelligence collector.

H2 View's own site (h2-view.com) and its RSS feed are dead — H2 View has been
absorbed into gasworld.com and now publishes as a card-listing channel page
there (https://www.gasworld.com/h2-view/). Follows the exact same pattern as
HydrogenCouncilCollector: real page download via shared_engine.run_sources()
-> hintco_collector.process_source() -> fetch_page() (Playwright), with
structured parsing handled by H2ViewParser via the shared ParserRegistry.
"""

from __future__ import annotations

from typing import Any

from config import H2_VIEW_SOURCES

from collectors.base_collector import BaseCollector
from collectors.shared_engine import run_sources


class H2ViewCollector(BaseCollector):
    """H2 View collector."""

    collector_id = "h2_view"
    collector_name = "H2 View"
    enabled = True

    @property
    def sources(self) -> list[dict]:
        return [
            {**source, "enabled": source.get("enabled", True)}
            for source in H2_VIEW_SOURCES
        ]

    def run(self, selected_source_ids: list[str] | None = None) -> list[Any]:
        valid, message = self.validate_configuration()
        if not valid:
            raise ValueError(message)
        return run_sources(self.get_selected_sources(selected_source_ids))
