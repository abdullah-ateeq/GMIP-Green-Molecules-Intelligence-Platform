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
from gmip.models.raw_document import RawDocument  # noqa: E402


def _fake_raw_documents() -> list[RawDocument]:
    return [
        RawDocument(
            source_id="h2_view",
            source_name="H2 View",
            source_url="https://www.h2-view.com/story/example/",
            title="A new green hydrogen plant is announced",
            text="A new green hydrogen plant is announced in Germany.",
        )
    ]


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


def test_h2_view_sources_use_registry_feed_url_not_a_duplicate() -> None:
    from gmip.config import get_source_definition

    collector = H2ViewCollector()
    registry_source = get_source_definition("h2_view")

    assert collector.sources == [
        {
            "source_id": "h2_view",
            "source_name": "H2 View",
            "url": registry_source.feed_url,
            "source_type": registry_source.source_category.value,
            "enabled": True,
        }
    ]


def test_h2_view_selectable_by_source_id_runs_only_h2_view(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    with patch(
        "collectors.h2_view_collector.GmipH2ViewCollector.collect",
        return_value=_fake_raw_documents(),
    ):
        manager = CollectorManager()
        results = manager.run_selected_sources(["h2_view"])

    assert len(results) == 1
    assert results[0].source_id == "h2_view"
    assert results[0].status == "SUCCESS"


def test_rss_entries_are_converted_and_persisted(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    with patch(
        "collectors.h2_view_collector.GmipH2ViewCollector.collect",
        return_value=_fake_raw_documents(),
    ):
        collector = H2ViewCollector()
        results = collector.run()

    assert len(results) == 1
    assert "1 new" in results[0].message

    rows = database.get_recent_intelligence_objects(source_id="h2_view")
    assert len(rows) == 1
    assert "green hydrogen plant" in rows[0]["title"].lower()


def test_empty_feed_returns_no_items_result_without_crashing(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    with patch(
        "collectors.h2_view_collector.GmipH2ViewCollector.collect",
        return_value=[],
    ):
        collector = H2ViewCollector()
        results = collector.run()

    assert len(results) == 1
    assert results[0].status == "NO_ITEMS"
    assert results[0].error is None


def test_feed_failure_returns_error_result_without_crashing(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    with patch(
        "collectors.h2_view_collector.GmipH2ViewCollector.collect",
        side_effect=RuntimeError("feed unreachable"),
    ):
        collector = H2ViewCollector()
        results = collector.run()

    assert len(results) == 1
    assert results[0].status == "FEED_ERROR"
    assert "feed unreachable" in results[0].error


def test_collector_manager_survives_h2_view_failure(tmp_path, monkeypatch) -> None:
    """
    A broken H2 View feed must not stop Hintco/Hydrogen Council results
    from coming back (CollectorManager's own per-collector isolation).
    """
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    with patch(
        "collectors.h2_view_collector.GmipH2ViewCollector.collect",
        side_effect=RuntimeError("feed unreachable"),
    ):
        manager = CollectorManager()
        results = manager.run_selected_sources(["h2_view"])

    assert len(results) == 1
    assert results[0].status == "FEED_ERROR"
