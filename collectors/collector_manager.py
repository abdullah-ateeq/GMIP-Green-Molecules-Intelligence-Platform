"""Collector manager for GMIP market intelligence sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from collectors.h2_view_collector import H2ViewCollector
from collectors.hintco_collector import HintcoCollector
from collectors.hydrogen_council_collector import (
    HydrogenCouncilCollector,
)


@dataclass
class CollectorErrorResult:
    """Standard result returned when a collector itself fails."""

    source_id: str
    source_name: str
    source_url: str
    status: str
    relevant: bool
    products: list[str]
    event_types: list[str]
    message: str
    error: str | None = None


class CollectorManager:
    """Register, inspect, and execute GMIP collectors."""

    def __init__(self) -> None:
        """Register all available GMIP collectors."""

        self.collectors = [
            HintcoCollector(),
            HydrogenCouncilCollector(),
            H2ViewCollector(),
        ]

    def get_enabled_collectors(self) -> list[Any]:
        """Return all enabled collectors."""

        return [
            collector
            for collector in self.collectors
            if collector.enabled
        ]

    def get_collector_statuses(self) -> list[dict]:
        """Return collector-level status information."""

        return [
            collector.get_status()
            for collector in self.collectors
        ]

    def get_source_statuses(self) -> list[dict]:
        """Return source-level metadata for all registered collectors."""

        source_statuses: list[dict] = []

        for collector in self.collectors:
            source_statuses.extend(
                collector.get_source_statuses()
            )

        return source_statuses

    def get_collector(
        self,
        collector_id: str,
    ) -> Any | None:
        """Find one collector by its unique collector ID."""

        for collector in self.collectors:
            if collector.collector_id == collector_id:
                return collector

        return None

    def run_all_collectors(self) -> list[Any]:
        """
        Run every enabled collector and every enabled source.

        Returns:
            Combined collection results from all enabled collectors.
        """

        enabled_collector_ids = [
            collector.collector_id
            for collector in self.get_enabled_collectors()
        ]

        return self.run_selected_collectors(
            collector_ids=enabled_collector_ids
        )

    def run_selected_collectors(
        self,
        collector_ids: list[str],
    ) -> list[Any]:
        """
        Run all enabled sources belonging to selected collectors.

        Args:
            collector_ids:
                Collector IDs selected by the user.

        Returns:
            Combined results from the selected collectors.
        """

        selected_ids = set(collector_ids)
        combined_results: list[Any] = []

        for collector in self.get_enabled_collectors():

            if collector.collector_id not in selected_ids:
                continue

            collector_results = self._run_collector(
                collector=collector,
                selected_source_ids=None,
            )

            combined_results.extend(collector_results)

        return combined_results

    def run_selected_sources(
        self,
        source_ids: list[str],
    ) -> list[Any]:
        """
        Run only the exact enabled sources selected by the user.

        The manager automatically determines which collector owns
        each selected source.

        Args:
            source_ids:
                Source IDs selected by the user.

        Returns:
            Combined results for all matching sources.
        """

        selected_ids = set(source_ids)
        combined_results: list[Any] = []

        for collector in self.get_enabled_collectors():

            collector_source_ids = {
                source["source_id"]
                for source in collector.get_enabled_sources()
            }

            matching_source_ids = sorted(
                selected_ids.intersection(
                    collector_source_ids
                )
            )

            if not matching_source_ids:
                continue

            collector_results = self._run_collector(
                collector=collector,
                selected_source_ids=matching_source_ids,
            )

            combined_results.extend(collector_results)

        return combined_results

    def _run_collector(
        self,
        collector: Any,
        selected_source_ids: list[str] | None,
    ) -> list[Any]:
        """
        Run one collector safely.

        A collector failure is converted into a standard error result
        so that one failed collector does not stop other collectors.
        """

        try:
            results = collector.run(
                selected_source_ids=selected_source_ids
            )

            if results is None:
                return []

            return list(results)

        except Exception as exc:
            return [
                CollectorErrorResult(
                    source_id=collector.collector_id,
                    source_name=collector.collector_name,
                    source_url="",
                    status="COLLECTOR_ERROR",
                    relevant=False,
                    products=[],
                    event_types=[],
                    message=(
                        f"{collector.collector_name} collector failed."
                    ),
                    error=str(exc),
                )
            ]