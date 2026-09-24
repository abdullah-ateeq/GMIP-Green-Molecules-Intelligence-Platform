"""Background worker for running the market intelligence collector."""

from __future__ import annotations

from time import perf_counter

from PySide6.QtCore import QThread, Signal

from database import complete_collection_run, start_collection_run
from collectors.collector_manager import CollectorManager


class ScanWorker(QThread):
    """Run market intelligence collectors without blocking the GUI."""

    scan_completed = Signal(dict)
    scan_failed = Signal(str)

    ERROR_STATUSES = {
        "BROWSER_TIMEOUT",
        "HTTP_ERROR",
        "TIMEOUT_ERROR",
        "REQUEST_ERROR",
        "PROCESSING_ERROR",
        "COLLECTOR_ERROR",
    }

    CHANGE_STATUSES = {"CHANGED"}

    def __init__(
        self,
        parent=None,
        selected_source_ids: list[str] | tuple[str, ...] | None = None,
    ):
        """
        Create a background scan worker.

        Args:
            parent:
                Optional Qt parent object.

            selected_source_ids:
                Source IDs to scan.

                - None: scan all enabled collectors and sources.
                - A list/tuple: scan only those source IDs.
                - An empty list/tuple: run a valid scan with zero sources.
        """
        super().__init__(parent)

        self.selected_source_ids = (
            None
            if selected_source_ids is None
            else tuple(selected_source_ids)
        )

    def run(self) -> None:
        started = perf_counter()
        run_id: int | None = None

        try:
            run_id = start_collection_run()
            manager = CollectorManager()

            if self.selected_source_ids is None:
                results = manager.run_all_collectors()
            else:
                results = manager.run_selected_sources(
                    list(self.selected_source_ids)
                )

            sources_checked = len(results)
            sources_changed = sum(
                result.status in self.CHANGE_STATUSES
                for result in results
            )
            errors_count = sum(
                bool(result.error)
                or result.status in self.ERROR_STATUSES
                for result in results
            )
            new_baselines = sum(
                result.status == "INITIAL_SNAPSHOT"
                for result in results
            )

            duration_seconds = perf_counter() - started
            run_message = (
                f"Checked {sources_checked} sources; "
                f"detected {sources_changed} changes; "
                f"created {new_baselines} initial baselines; "
                f"encountered {errors_count} errors."
            )

            complete_collection_run(
                run_id=run_id,
                sources_checked=sources_checked,
                sources_changed=sources_changed,
                errors_count=errors_count,
                run_message=run_message,
            )

            self.scan_completed.emit(
                {
                    "sources_checked": sources_checked,
                    "sources_changed": sources_changed,
                    "new_baselines": new_baselines,
                    "errors_count": errors_count,
                    "duration_seconds": duration_seconds,
                    "results": results,
                }
            )

        except Exception as exc:
            if run_id is not None:
                try:
                    complete_collection_run(
                        run_id=run_id,
                        sources_checked=0,
                        sources_changed=0,
                        errors_count=1,
                        run_message=f"Market scan failed: {exc}",
                    )
                except Exception:
                    pass

            self.scan_failed.emit(str(exc))
