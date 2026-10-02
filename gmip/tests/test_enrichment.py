from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
from gmip.enrichment import enrich_hydrogen_council_articles  # noqa: E402
from gmip.intelligence.enums import IntelligenceType  # noqa: E402
from gmip.intelligence.intelligence_object import IntelligenceObject  # noqa: E402
from hintco_collector import AccessBlockedError  # noqa: E402

REAL_ARTICLE_HTML = """
<html><head><title>Six new members join Hydrogen Council</title></head>
<body>
<main>
<h1>Six new members join Hydrogen Council, strengthening global
collaboration across the industry</h1>
<p>BRUSSELS, September 29, 2026 - The Hydrogen Council today welcomes
six new members: Acwa, EcoLog, Hydrom, Mitsui O.S.K Lines, TANAKA, and
2JCP.</p>
<p>Acwa is a global developer, investor and operator across power,
water and renewable hydrogen, including through its role in the NEOM
Green Hydrogen Project. Acwa is developing the Yanbu Green Hydrogen Hub
in Saudi Arabia.</p>
</main>
</body></html>
"""


def _setup_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()


def _teaser_object(
    title: str = "Six new members join Hydrogen Council, strengthening "
    "global collaboration across the industry",
    source_url: str = "https://hydrogencouncil.com/en/six-new-members/",
) -> IntelligenceObject:
    return IntelligenceObject(
        title=title,
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url=source_url,
        intelligence_type=IntelligenceType.NEWS,
        companies=[],
        projects=[],
    )


def test_enrichment_extracts_companies_and_projects_from_full_text(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = _teaser_object()
    database.save_intelligence_object(obj)

    with patch(
        "gmip.enrichment.download_page_with_browser",
        return_value=REAL_ARTICLE_HTML,
    ):
        report = enrich_hydrogen_council_articles(limit=10)

    assert report["articles_attempted"] == 1
    assert report["articles_enriched"] == 1
    assert report["new_company_mentions"] >= 5
    assert report["new_project_mentions"] >= 1

    rows = database.get_recent_intelligence_objects(source_id="hydrogen_council")
    enriched_row = [r for r in rows if r["source_url"] == obj.source_url][0]
    import json

    companies = json.loads(enriched_row["companies"])
    assert "EcoLog" in companies
    assert "Hydrom" in companies
    assert "TANAKA" in companies


def test_enrichment_does_not_create_a_duplicate_record(
    tmp_path, monkeypatch
) -> None:
    """
    The enriched version shares the original's identity_key (same
    title + source_id) — it must be classified as an update to the same
    logical item, never a brand-new unrelated record.
    """
    _setup_db(tmp_path, monkeypatch)

    obj = _teaser_object()
    database.save_intelligence_object(obj)

    with patch(
        "gmip.enrichment.download_page_with_browser",
        return_value=REAL_ARTICLE_HTML,
    ):
        enrich_hydrogen_council_articles(limit=10)

    with database.get_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS total FROM intelligence_objects "
            "WHERE identity_key = ?",
            (obj.identity_key,),
        ).fetchone()["total"]

    # Two rows (original teaser + enriched update) share one identity_key
    # — that's the established NEW/UPDATED versioning pattern, not a
    # duplicate under a different identity.
    assert count == 2


def test_enrichment_skips_already_enriched_articles(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = _teaser_object()
    database.save_intelligence_object(obj)

    with patch(
        "gmip.enrichment.download_page_with_browser",
        return_value=REAL_ARTICLE_HTML,
    ) as mock_download:
        enrich_hydrogen_council_articles(limit=10)
        second_report = enrich_hydrogen_council_articles(limit=10)

    assert second_report["articles_attempted"] == 0
    assert mock_download.call_count == 1


def test_enrichment_handles_cloudflare_block_gracefully(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = _teaser_object()
    database.save_intelligence_object(obj)

    with patch(
        "gmip.enrichment.download_page_with_browser",
        side_effect=AccessBlockedError("Cloudflare challenge page detected"),
    ):
        report = enrich_hydrogen_council_articles(limit=10)

    assert report["articles_attempted"] == 1
    assert report["articles_blocked"] == 1
    assert report["articles_enriched"] == 0

    # The original teaser record must still exist untouched.
    rows = database.get_recent_intelligence_objects(source_id="hydrogen_council")
    assert len(rows) == 1


def test_enrichment_one_article_failure_does_not_affect_another(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj_a = _teaser_object(
        title="Article A", source_url="https://hydrogencouncil.com/en/article-a/"
    )
    obj_b = _teaser_object(
        title="Article B", source_url="https://hydrogencouncil.com/en/article-b/"
    )
    database.save_intelligence_object(obj_a)
    database.save_intelligence_object(obj_b)

    def fake_download(url: str) -> str:
        if "article-a" in url:
            raise RuntimeError("boom")
        return REAL_ARTICLE_HTML

    with patch(
        "gmip.enrichment.download_page_with_browser", side_effect=fake_download
    ):
        report = enrich_hydrogen_council_articles(limit=10)

    assert report["articles_attempted"] == 2
    assert report["articles_failed"] == 1
    assert report["articles_enriched"] == 1


def test_enrichment_excludes_hydrogen_council_self_mention(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = _teaser_object()
    database.save_intelligence_object(obj)

    with patch(
        "gmip.enrichment.download_page_with_browser",
        return_value=REAL_ARTICLE_HTML,
    ):
        enrich_hydrogen_council_articles(limit=10)

    rows = database.get_recent_intelligence_objects(source_id="hydrogen_council")
    enriched_row = [r for r in rows if r["source_url"] == obj.source_url][0]
    import json

    companies = json.loads(enriched_row["companies"])
    assert "Hydrogen Council" not in companies


def test_listing_pages_are_never_enrichment_candidates(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    homepage = IntelligenceObject(
        title="Some whole-page object",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/newsroom/",
        intelligence_type=IntelligenceType.NEWS,
    )
    database.save_intelligence_object(homepage)

    with patch(
        "gmip.enrichment.download_page_with_browser",
        return_value=REAL_ARTICLE_HTML,
    ) as mock_download:
        report = enrich_hydrogen_council_articles(limit=10)

    assert report["articles_attempted"] == 0
    mock_download.assert_not_called()
