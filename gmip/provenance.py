"""
Source URL availability checking.

Verifies whether a previously-collected IntelligenceObject.source_url
still resolves to real content. Deliberately a separate, on-demand
maintenance pass (recheck_source_availability()) rather than something
run synchronously during every collection — checking every discovered
article link over the network on every run would make ordinary
collection far slower and heavier than it needs to be, and most links
don't change status day to day.

See the provenance-quality brief: a GMIP record must never imply its
source is trustworthy merely because a URL was once collected.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 15

# A definitive "gone" status — the server itself confirms the resource no
# longer exists. Anything else that prevents a clean check (403, 429,
# 5xx, timeout, connection error) is reported as UNVERIFIED, never
# UNAVAILABLE — a site blocking automated requests is not the same as a
# source being gone, and conflating the two would produce false "this
# intelligence is no longer backed by evidence" signals.
DEFINITIVELY_UNAVAILABLE_STATUSES = {404, 410}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def check_url_availability(
    url: str,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Check whether `url` still resolves to real content.

    Returns {"available", "status", "http_status", "final_url",
    "checked_at"}. "status" is one of "AVAILABLE", "UNAVAILABLE",
    "UNVERIFIED"; "available" is True/False/None to match.
    """
    checked_at = datetime.now(timezone.utc)

    try:
        response = requests.head(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
        )

        # Some servers don't implement HEAD properly — fall back to GET
        # before giving up on this URL.
        if response.status_code in (405, 501):
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                allow_redirects=True,
                stream=True,
            )

    except requests.RequestException as exc:
        logger.info(
            "Source availability check failed for %s: %s", url, exc
        )
        return {
            "available": None,
            "status": "UNVERIFIED",
            "http_status": None,
            "final_url": url,
            "checked_at": checked_at,
        }

    if response.status_code in DEFINITIVELY_UNAVAILABLE_STATUSES:
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "http_status": response.status_code,
            "final_url": response.url,
            "checked_at": checked_at,
        }

    if 200 <= response.status_code < 300:
        return {
            "available": True,
            "status": "AVAILABLE",
            "http_status": response.status_code,
            "final_url": response.url,
            "checked_at": checked_at,
        }

    return {
        "available": None,
        "status": "UNVERIFIED",
        "http_status": response.status_code,
        "final_url": response.url,
        "checked_at": checked_at,
    }


def recheck_source_availability(limit: int = 50) -> list[dict]:
    """
    Run a real availability check against every IntelligenceObject whose
    source_url has never been checked, persisting each result.
    """
    import database

    candidates = database.get_intelligence_objects_needing_source_check(
        limit=limit
    )
    results = []

    for candidate in candidates:
        result = check_url_availability(candidate["source_url"])

        database.update_source_availability(
            intelligence_id=candidate["intelligence_id"],
            available=result["available"],
            status=result["status"],
            http_status=result["http_status"],
            checked_at=result["checked_at"],
        )

        results.append(
            {"intelligence_id": candidate["intelligence_id"], **result}
        )

    return results
