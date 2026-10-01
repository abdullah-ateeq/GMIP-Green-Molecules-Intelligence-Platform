"""Shared execution engine for GMIP website collectors."""

from __future__ import annotations

from collections.abc import Iterable

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import database
from hintco_collector import AccessBlockedError, process_source
from models import CollectionResult

# Legacy per-source CollectionResult.status values that represent a real,
# successful page fetch (change-detected or not) — anything else is a
# failure of some kind for source-health purposes.
_SUCCESS_STATUSES = {"INITIAL_SNAPSHOT", "CHANGED", "NO_CHANGE"}


def _registry_source_id(page_source_id: str) -> str:
    """
    Map a page-level source_id (e.g. "hydrogen_council_newsroom") to the
    registry-level source_id the `sources` table / Sources page actually
    tracks (e.g. "hydrogen_council"). H2 View has exactly one page, so it
    maps to itself.
    """
    from config import H2_VIEW_SOURCES, HINTCO_SOURCES, HYDROGEN_COUNCIL_SOURCES

    page_groups = (
        (HINTCO_SOURCES, "hintco"),
        (HYDROGEN_COUNCIL_SOURCES, "hydrogen_council"),
        (H2_VIEW_SOURCES, "h2_view"),
    )

    for sources, registry_source_id in page_groups:
        if any(s["source_id"] == page_source_id for s in sources):
            return registry_source_id

    return page_source_id


def run_sources(
    sources: Iterable[dict],
) -> list[CollectionResult]:
    """
    Process a collection of source definitions.

    This function is independent of a particular collector. Hintco,
    Hydrogen Council, H2 View, and future collectors all pass their
    selected source dictionaries into this shared execution engine.

    Every attempt is recorded via database.record_source_attempt() (per
    real page_source_id) — separate from whether this specific run
    detected a content change — so the Sources page can distinguish
    "the collector/parser implementation is broken" from "this source is
    temporarily blocked by access control", and so a transient block
    never erases the last successfully collected intelligence.
    """

    results: list[CollectionResult] = []

    for source in sources:
        print(f"\nChecking {source['source_name']}...")

        try:
            result = process_source(source)

        except AccessBlockedError as exc:
            result = _create_error_result(
                source=source,
                status="BLOCKED_BY_ACCESS_CONTROL",
                message=(
                    "The source is currently blocked by an access-control "
                    "challenge (e.g. Cloudflare). GMIP does not attempt to "
                    "bypass this — it will retry on the next normal "
                    "scheduled collection."
                ),
                error=exc,
            )

        except PlaywrightTimeoutError as exc:
            result = _create_error_result(
                source=source,
                status="BROWSER_TIMEOUT",
                message=(
                    "The browser opened the page, but it did not "
                    "finish loading."
                ),
                error=exc,
            )

        except requests.HTTPError as exc:
            result = _create_error_result(
                source=source,
                status="HTTP_ERROR",
                message="The source returned an HTTP error.",
                error=exc,
            )

        except requests.Timeout as exc:
            result = _create_error_result(
                source=source,
                status="TIMEOUT_ERROR",
                message="The request timed out.",
                error=exc,
            )

        except requests.RequestException as exc:
            result = _create_error_result(
                source=source,
                status="REQUEST_ERROR",
                message="The request failed.",
                error=exc,
            )

        except Exception as exc:
            result = _create_error_result(
                source=source,
                status="PROCESSING_ERROR",
                message="Unexpected processing error.",
                error=exc,
            )

        _record_attempt(result)
        results.append(result)

    return results


def _record_attempt(result: CollectionResult) -> None:
    attempt_status = (
        "SUCCESS" if result.status in _SUCCESS_STATUSES else result.status
    )

    try:
        database.record_source_attempt(
            source_id=_registry_source_id(result.source_id),
            status=attempt_status,
            error=result.error,
        )
    except Exception as exc:
        # Source-health bookkeeping must never break the actual
        # collection run it's recording.
        print(f"Failed to record source attempt for {result.source_id}: {exc}")


def _create_error_result(
    source: dict,
    status: str,
    message: str,
    error: Exception,
) -> CollectionResult:
    """Create a standard result when one source fails."""

    return CollectionResult(
        source_id=source["source_id"],
        source_name=source["source_name"],
        source_url=source["url"],
        status=status,
        relevant=False,
        products=[],
        event_types=[],
        message=message,
        error=str(error),
    )
