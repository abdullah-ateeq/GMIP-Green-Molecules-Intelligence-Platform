from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
from gmip.intelligence.enums import IntelligenceType  # noqa: E402
from gmip.intelligence.intelligence_object import IntelligenceObject  # noqa: E402


def _make_object(title: str = "Test intelligence item") -> IntelligenceObject:
    return IntelligenceObject(
        title=title,
        source_organisation="H2 View",
        source_id="h2_view",
        source_url="https://www.h2-view.com/story/example/",
        intelligence_type=IntelligenceType.NEWS,
        parser_name="H2ViewParser",
    )


def test_save_and_retrieve_intelligence_object(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    obj = _make_object()
    inserted = database.save_intelligence_object(obj)

    assert inserted is True

    rows = database.get_recent_intelligence_objects(
        limit=10, source_id="h2_view"
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Test intelligence item"
    assert rows[0]["intelligence_type"] == "news"


def test_saving_same_content_twice_does_not_duplicate(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    obj = _make_object()
    first = database.save_intelligence_object(obj)
    second = database.save_intelligence_object(obj)

    assert first is True
    assert second is False

    rows = database.get_recent_intelligence_objects(source_id="h2_view")
    assert len(rows) == 1


def test_different_source_ids_are_isolated(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    hintco_obj = IntelligenceObject(
        title="A Hintco tender",
        source_organisation="Hintco",
        source_id="hintco",
        source_url="https://hintco.eu/hpa-auctions/",
        intelligence_type=IntelligenceType.TENDER,
    )
    h2_view_obj = _make_object("An H2 View story")

    database.save_intelligence_object(hintco_obj)
    database.save_intelligence_object(h2_view_obj)

    all_rows = database.get_recent_intelligence_objects(limit=10)
    hintco_rows = database.get_recent_intelligence_objects(
        source_id="hintco"
    )

    assert len(all_rows) == 2
    assert len(hintco_rows) == 1
    assert hintco_rows[0]["title"] == "A Hintco tender"
