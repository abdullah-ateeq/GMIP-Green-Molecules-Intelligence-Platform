from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
from gmip.models.raw_document import RawDocument  # noqa: E402


def _doc(source_id: str = "hintco_news") -> RawDocument:
    return RawDocument(
        source_id=source_id,
        source_name="Hintco News",
        source_url="https://hintco.eu/news/",
        title="Hintco News",
        text="Some collected page text." * 200,  # exercise the excerpt cap
        status="SUCCESS",
    )


def test_save_and_retrieve_raw_document(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    document = _doc()
    database.save_raw_document(document)

    rows = database.get_recent_raw_documents(source_id="hintco_news")
    assert len(rows) == 1
    assert rows[0]["document_id"] == document.document_id
    assert rows[0]["source_url"] == "https://hintco.eu/news/"
    # Excerpt is bounded even though the source text is much longer.
    assert len(rows[0]["text_excerpt"]) <= 2000


def test_every_collection_attempt_is_logged_not_deduplicated(
    tmp_path, monkeypatch
) -> None:
    """
    Unlike intelligence_objects, raw_documents is an audit trail — every
    fetch is recorded even if the content is identical to the last one.
    """
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    database.save_raw_document(_doc())
    database.save_raw_document(_doc())

    rows = database.get_recent_raw_documents(source_id="hintco_news")
    assert len(rows) == 2


def test_raw_documents_are_isolated_by_source_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    database.save_raw_document(_doc("hintco_news"))
    database.save_raw_document(_doc("hydrogen_council_intelligence"))

    all_rows = database.get_recent_raw_documents(limit=10)
    hintco_rows = database.get_recent_raw_documents(source_id="hintco_news")

    assert len(all_rows) == 2
    assert len(hintco_rows) == 1
