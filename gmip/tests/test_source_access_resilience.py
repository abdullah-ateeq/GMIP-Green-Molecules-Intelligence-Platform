from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
from collectors.shared_engine import run_sources  # noqa: E402
from gmip.config import SOURCE_REGISTRY  # noqa: E402
from hintco_collector import AccessBlockedError, validate_downloaded_page  # noqa: E402


def _setup_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()
    database.sync_source_registry(SOURCE_REGISTRY)


CLOUDFLARE_CHALLENGE_HTML = (
    "<html><head><title>Just a moment...</title></head>"
    "<body>Checking your browser before accessing the site."
    + ("x" * 300)
    + "</body></html>"
)


# ------------------------------------------------------------
# validate_downloaded_page -> AccessBlockedError
# ------------------------------------------------------------


def test_cloudflare_challenge_raises_access_blocked_not_generic_error() -> None:
    try:
        validate_downloaded_page(
            url="https://www.gasworld.com/h2-view/",
            html=CLOUDFLARE_CHALLENGE_HTML,
            status_code=200,
        )
        assert False, "expected AccessBlockedError"
    except AccessBlockedError:
        pass


def test_plain_404_raises_plain_runtime_error_not_access_blocked() -> None:
    """
    A normal HTTP error page must not be misclassified as an access-
    control block — they're handled (and reported) differently.
    """
    try:
        validate_downloaded_page(
            url="https://www.gasworld.com/story/gone/1.article/",
            html="<html><body>" + ("x" * 300) + "</body></html>",
            status_code=404,
        )
        assert False, "expected an error"
    except AccessBlockedError:
        assert False, "a plain 404 must not raise AccessBlockedError"
    except RuntimeError:
        pass


# ------------------------------------------------------------
# shared_engine.run_sources() classification + source-health recording
# ------------------------------------------------------------


def test_cloudflare_block_classified_and_does_not_crash(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    source = {
        "source_id": "h2_view",
        "source_name": "H2 View",
        "url": "https://www.gasworld.com/h2-view/",
        "source_type": "Industry Media",
        "enabled": True,
    }

    with patch(
        "collectors.shared_engine.process_source",
        side_effect=AccessBlockedError("Cloudflare challenge page detected"),
    ):
        results = run_sources([source])

    assert len(results) == 1
    assert results[0].status == "BLOCKED_BY_ACCESS_CONTROL"
    assert results[0].error is not None

    status = database.get_source_registry_status()
    h2_view_status = next(s for s in status if s["source_id"] == "h2_view")
    assert h2_view_status["last_status"] == "BLOCKED_BY_ACCESS_CONTROL"
    assert h2_view_status["access_status"] == "BLOCKED"
    assert h2_view_status["implementation_status"] == "HEALTHY"


def test_blocked_attempt_preserves_previous_successful_collection(
    tmp_path, monkeypatch
) -> None:
    """
    Section 5 of the access-resilience brief: a temporary access block
    must never erase the record of the last successful collection.
    """
    _setup_db(tmp_path, monkeypatch)

    database.record_source_attempt("h2_view", status="SUCCESS")
    status_after_success = database.get_source_registry_status()
    h2_view = next(s for s in status_after_success if s["source_id"] == "h2_view")
    first_success_time = h2_view["last_successful_at"]
    assert first_success_time is not None

    database.record_source_attempt(
        "h2_view",
        status="BLOCKED_BY_ACCESS_CONTROL",
        error="Cloudflare challenge page detected",
    )

    status_after_block = database.get_source_registry_status()
    h2_view = next(s for s in status_after_block if s["source_id"] == "h2_view")

    assert h2_view["last_successful_at"] == first_success_time
    assert h2_view["last_status"] == "BLOCKED_BY_ACCESS_CONTROL"
    assert h2_view["access_status"] == "BLOCKED"


def test_internal_processing_error_flagged_as_implementation_issue(
    tmp_path, monkeypatch
) -> None:
    """
    An access block and an actual bug in our own code must be
    distinguishable — only the latter should read as "needs attention".
    """
    _setup_db(tmp_path, monkeypatch)

    database.record_source_attempt(
        "h2_view", status="PROCESSING_ERROR", error="KeyError: 'title'"
    )

    status = database.get_source_registry_status()
    h2_view = next(s for s in status if s["source_id"] == "h2_view")

    assert h2_view["implementation_status"] == "NEEDS_ATTENTION"
    assert h2_view["access_status"] == "NORMAL"


# ------------------------------------------------------------
# Freshness
# ------------------------------------------------------------


def test_freshness_never_collected_when_no_successful_attempt(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    status = database.get_source_registry_status()
    h2_view = next(s for s in status if s["source_id"] == "h2_view")

    assert h2_view["freshness"] == "NEVER_COLLECTED"


def test_freshness_current_right_after_success(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)

    database.record_source_attempt("h2_view", status="SUCCESS")

    status = database.get_source_registry_status()
    h2_view = next(s for s in status if s["source_id"] == "h2_view")

    assert h2_view["freshness"] == "CURRENT"


def test_freshness_very_stale_after_a_week(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)

    database.record_source_attempt("h2_view", status="SUCCESS")

    old_time = (datetime.now() - timedelta(days=10)).isoformat(
        timespec="seconds"
    )

    with database.get_connection() as connection:
        connection.execute(
            "UPDATE sources SET last_successful_at = ? WHERE source_id = ?",
            (old_time, "h2_view"),
        )

    status = database.get_source_registry_status()
    h2_view = next(s for s in status if s["source_id"] == "h2_view")

    assert h2_view["freshness"] == "VERY_STALE"
