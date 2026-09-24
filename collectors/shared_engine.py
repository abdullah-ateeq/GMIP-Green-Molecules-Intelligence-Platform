"""Shared execution engine for GMIP website collectors."""

from __future__ import annotations

from collections.abc import Iterable

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from hintco_collector import process_source
from models import CollectionResult


def run_sources(
    sources: Iterable[dict],
) -> list[CollectionResult]:
    """
    Process a collection of source definitions.

    This function is independent of a particular collector. Hintco,
    Hydrogen Council, and future collectors can all pass their selected
    source dictionaries into this shared execution engine.
    """

    results: list[CollectionResult] = []

    for source in sources:
        print(f"\nChecking {source['source_name']}...")

        try:
            result = process_source(source)

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

        results.append(result)

    return results


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