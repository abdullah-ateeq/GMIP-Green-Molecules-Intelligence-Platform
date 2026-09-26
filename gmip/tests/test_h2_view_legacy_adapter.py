from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
from collectors.collector_manager import CollectorManager  # noqa: E402
from collectors.h2_view_collector import H2ViewCollector  # noqa: E402

# A trimmed-down but structurally faithful reconstruction of
# gasworld.com/h2-view/'s real layout (see gmip/tests/test_h2_view_parser.py
# for the same fixture pattern) — used here to exercise the collector
# end-to-end (page download -> parse -> persist) without any live network
# call. Playwright's actual page download is mocked at
# hintco_collector.download_page_with_browser, one level below fetch_page(),
# so fetch_page()/process_source()/parse_and_persist_intelligence() all run
# for real.
FAKE_H2_VIEW_HTML = """
<html><head><title>H2 View | gasworld</title></head><body>
<div class="signals-grid">
  <div class="card">
    <a href="https://www.gasworld.com/story/example-green-hydrogen-plant/2260001.article/">
      A new green hydrogen plant is announced in Germany
    </a>
    By Connor Jack
    A new green hydrogen plant has been announced in Germany this week.
    Hydrogen News 1 day ago 2 min read
  </div>
</div>
</body></html>
"""


def test_collector_manager_registers_h2_view() -> None:
    manager = CollectorManager()

    collector = manager.get_collector("h2_view")

    assert collector is not None
    assert isinstance(collector, H2ViewCollector)


def test_h2_view_appears_among_enabled_collectors() -> None:
    manager = CollectorManager()

    enabled_ids = [c.collector_id for c in manager.get_enabled_collectors()]

    assert "h2_view" in enabled_ids


def test_h2_view_appears_in_collector_statuses() -> None:
    manager = CollectorManager()

    statuses = {
        status["collector_id"]: status
        for status in manager.get_collector_statuses()
    }

    assert "h2_view" in statuses
    assert statuses["h2_view"]["configuration_valid"] is True
    assert statuses["h2_view"]["source_count"] == 1


def test_h2_view_appears_in_source_statuses() -> None:
    manager = CollectorManager()

    source_ids = [s["source_id"] for s in manager.get_source_statuses()]

    assert "h2_view" in source_ids


def test_h2_view_sources_come_from_config_not_duplicated() -> None:
    from config import H2_VIEW_SOURCES

    collector = H2ViewCollector()

    assert collector.sources == [
        {**source, "enabled": True} for source in H2_VIEW_SOURCES
    ]
    assert collector.sources[0]["url"] == "https://www.gasworld.com/h2-view/"


def test_h2_view_selectable_by_source_id_downloads_and_persists(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    with patch(
        "hintco_collector.download_page_with_browser",
        return_value=FAKE_H2_VIEW_HTML,
    ):
        manager = CollectorManager()
        results = manager.run_selected_sources(["h2_view"])

    assert len(results) == 1
    assert results[0].source_id == "h2_view"
    assert results[0].status in {"INITIAL_SNAPSHOT", "CHANGED", "NO_CHANGE"}

    rows = database.get_recent_intelligence_objects(source_id="h2_view")
    assert len(rows) == 1
    assert "green hydrogen plant" in rows[0]["title"].lower()
    assert rows[0]["source_url"] == (
        "https://www.gasworld.com/story/example-green-hydrogen-plant/2260001.article/"
    )


def test_collector_manager_survives_h2_view_download_failure(
    tmp_path, monkeypatch
) -> None:
    """
    A broken H2 View page download must not stop Hintco/Hydrogen Council
    results from coming back (CollectorManager's own per-collector
    isolation, via shared_engine.run_sources()'s per-source error handling).
    """
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    with patch(
        "hintco_collector.download_page_with_browser",
        side_effect=RuntimeError("page unreachable"),
    ):
        manager = CollectorManager()
        results = manager.run_selected_sources(["h2_view"])

    assert len(results) == 1
    assert results[0].status == "PROCESSING_ERROR"
