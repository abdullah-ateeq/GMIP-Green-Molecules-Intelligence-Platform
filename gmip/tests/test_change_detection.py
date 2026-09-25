from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
from gmip.intelligence.enums import IntelligenceType  # noqa: E402
from gmip.intelligence.intelligence_object import (  # noqa: E402
    IntelligenceObject,
    TenderDetails,
)


def _lot(status: str, title: str = "Global Lot (GL)") -> IntelligenceObject:
    return IntelligenceObject(
        title=title,
        source_organisation="Hintco",
        source_id="hintco",
        source_url="https://hintco.eu/hpa-auctions/",
        intelligence_type=IntelligenceType.TENDER,
        tender=TenderDetails(tender_status=status),
    )


def test_first_collection_is_classified_new(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    result = database.classify_and_save_intelligence_object(_lot("Open"))

    assert result["change_type"] == "NEW"
    assert result["inserted"] is True
    assert result["previous_intelligence_id"] is None


def test_identical_recollection_is_unchanged(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    database.classify_and_save_intelligence_object(_lot("Open"))
    result = database.classify_and_save_intelligence_object(_lot("Open"))

    assert result["change_type"] == "UNCHANGED"
    assert result["inserted"] is False


def test_changed_field_is_classified_updated_with_diff(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    database.classify_and_save_intelligence_object(_lot("Open"))
    result = database.classify_and_save_intelligence_object(_lot("Closed"))

    assert result["change_type"] == "UPDATED"
    assert result["inserted"] is True
    assert result["diff"]["tender_status"] == {"old": "Open", "new": "Closed"}


def test_different_identity_keys_do_not_collide(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    database.classify_and_save_intelligence_object(_lot("Open", "Global Lot (GL)"))
    result = database.classify_and_save_intelligence_object(
        _lot("Open", "African Lot (AFL)")
    )

    assert result["change_type"] == "NEW"


def test_identity_key_defaults_to_source_and_title() -> None:
    obj = _lot("Open", "Global Lot (GL)")
    assert obj.identity_key == "hintco:global lot (gl)"


def test_migration_adds_missing_columns_to_legacy_table(
    tmp_path, monkeypatch
) -> None:
    """
    Simulates a database created before identity_key/raw_document_id
    existed, and confirms initialize_database() migrates it additively
    without touching existing data.
    """
    import sqlite3

    db_path = tmp_path / "legacy.db"
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)

    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE intelligence_objects (
            intelligence_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_organisation TEXT,
            parser_name TEXT,
            intelligence_type TEXT,
            title TEXT NOT NULL,
            summary TEXT,
            source_url TEXT,
            published_at TEXT,
            products TEXT,
            countries TEXT,
            companies TEXT,
            categories TEXT,
            content_hash TEXT NOT NULL UNIQUE,
            payload_json TEXT NOT NULL,
            collected_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO intelligence_objects (
            intelligence_id, source_id, title, content_hash,
            payload_json, collected_at
        ) VALUES ('id-1', 'hintco', 'Pre-existing row', 'hash-1', '{}', '2026-01-01')
        """
    )
    connection.commit()
    connection.close()

    database.initialize_database()

    rows = database.get_recent_intelligence_objects(source_id="hintco")
    assert len(rows) == 1
    assert rows[0]["title"] == "Pre-existing row"
