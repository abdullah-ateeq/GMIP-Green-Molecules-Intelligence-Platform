from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
import hintco_collector  # noqa: E402
from gmip.models.raw_document import RawDocument  # noqa: E402


def _raw_document(source_id: str, text: str) -> RawDocument:
    return RawDocument(
        source_id=source_id,
        source_name=source_id,
        source_url=f"https://hintco.eu/{source_id}/",
        title=f"Hintco {source_id}",
        text=text,
    )


def test_unregistered_source_is_a_no_op() -> None:
    """No parser is registered for this made-up source_id — must not raise."""
    raw_document = _raw_document("not_a_real_source", "some text")

    hintco_collector._parse_and_persist_intelligence(raw_document)


def test_parser_failure_never_propagates(tmp_path, monkeypatch) -> None:
    """
    Hard guarantee from the phase brief: structured parsing must be purely
    additive. If the parser raises for any reason, legacy collection must
    be completely unaffected — this function must swallow the error.
    """
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    raw_document = _raw_document("hintco_news", "some text")

    with patch.object(
        hintco_collector._PARSER_REGISTRY,
        "get_parser",
        side_effect=RuntimeError("boom"),
    ):
        # Must not raise.
        hintco_collector._parse_and_persist_intelligence(raw_document)


def test_successful_parse_persists_intelligence(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()

    raw_document = _raw_document(
        "hintco_general_faq",
        "Frequently asked questions about the Hintco tender process.",
    )

    hintco_collector._parse_and_persist_intelligence(raw_document)

    rows = database.get_recent_intelligence_objects(source_id="hintco")
    assert len(rows) == 1
