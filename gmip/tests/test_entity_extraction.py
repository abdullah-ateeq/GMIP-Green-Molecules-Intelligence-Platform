from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
from gmip.entities.backfill import (  # noqa: E402
    resolve_mentions_for_object,
    run_entity_backfill,
)
from gmip.entities.resolver import resolve_mention  # noqa: E402
from gmip.intelligence.enums import IntelligenceType  # noqa: E402
from gmip.intelligence.intelligence_object import IntelligenceObject  # noqa: E402
from gmip.parsers.base_parser import BaseParser  # noqa: E402
from gmip.parsers.hintco_parser import HintcoParser  # noqa: E402
from gmip.parsers.hydrogen_council_parser import HydrogenCouncilParser  # noqa: E402


class _DummyParser(BaseParser):
    source_id = "dummy"

    def can_parse(self, raw_record: dict[str, Any]) -> bool:
        return True

    def parse(self, raw_record: dict[str, Any]) -> list[IntelligenceObject]:
        return []


def _setup_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()


# ------------------------------------------------------------
# Word-boundary safety (section 10)
# ------------------------------------------------------------


def test_extract_keywords_does_not_match_short_candidate_as_substring() -> None:
    """
    "BP" must not match inside "ABP" (a different real company name,
    Associated British Ports) — only a whole-word match counts.
    """
    matches = _DummyParser.extract_keywords(
        "ABP operates several UK ports.", ["BP"]
    )
    assert matches == []


def test_extract_keywords_does_not_match_nel_inside_panel() -> None:
    """
    "Nel" (the electrolyzer company) must not match inside "panel" —
    a real, likely false-positive risk given how often "panel
    discussion" appears in industry media text.
    """
    matches = _DummyParser.extract_keywords(
        "The CEO panel discussed market trends.", ["Nel"]
    )
    assert matches == []


def test_extract_keywords_still_matches_whole_word_short_candidate() -> None:
    matches = _DummyParser.extract_keywords(
        "BP announced a new hydrogen partnership.", ["BP"]
    )
    assert matches == ["BP"]


# ------------------------------------------------------------
# Relationship detection (base_parser.detect_relationships)
# ------------------------------------------------------------


def test_detect_relationships_from_explicit_develops_phrase() -> None:
    relationships = _DummyParser.detect_relationships(
        "ACWA Power is developing the NEOM Green Hydrogen Project in "
        "Saudi Arabia.",
        companies=["ACWA Power"],
        projects=["NEOM Green Hydrogen Project"],
    )

    assert len(relationships) == 1
    assert relationships[0] == {
        "subject": "ACWA Power",
        "subject_type": "COMPANY",
        "relationship_type": "develops",
        "object": "NEOM Green Hydrogen Project",
        "object_type": "PROJECT",
    }


def test_detect_relationships_passive_voice_developed_by() -> None:
    relationships = _DummyParser.detect_relationships(
        "The NEOM Green Hydrogen Project, developed by ACWA Power, is "
        "progressing on schedule.",
        companies=["ACWA Power"],
        projects=["NEOM Green Hydrogen Project"],
    )

    assert len(relationships) == 1
    assert relationships[0]["relationship_type"] == "develops"
    assert relationships[0]["subject"] == "ACWA Power"


def test_no_relationship_from_mere_co_mention() -> None:
    """
    Two names appearing independently in the same article — with no
    connecting verb phrase — must not produce a relationship (section 15
    of the entity-extraction brief).
    """
    relationships = _DummyParser.detect_relationships(
        "ACWA Power released its annual report. Separately, the NEOM "
        "Green Hydrogen Project marked a construction milestone.",
        companies=["ACWA Power"],
        projects=["NEOM Green Hydrogen Project"],
    )

    assert relationships == []


def test_detect_relationships_company_partnership() -> None:
    relationships = _DummyParser.detect_relationships(
        "ACWA Power partners with Air Products on a new initiative.",
        companies=["ACWA Power", "Air Products"],
        projects=[],
    )

    assert len(relationships) == 1
    assert relationships[0] == {
        "subject": "ACWA Power",
        "subject_type": "COMPANY",
        "relationship_type": "partners_with",
        "object": "Air Products",
        "object_type": "COMPANY",
    }


# ------------------------------------------------------------
# Hydrogen Council: project extraction + no false project
# ------------------------------------------------------------


def test_hydrogen_council_extracts_explicit_project_name() -> None:
    parser = HydrogenCouncilParser()
    raw_record = {
        "source_id": "hydrogen_council_newsroom",
        "source_url": "https://hydrogencouncil.com/en/newsroom/",
        "title": "Hydrogen Council Newsroom",
        "text": (
            "Media Release September 10, 2026 "
            "ACWA Power progresses NEOM Green Hydrogen Project "
            "ACWA Power is developing the NEOM Green Hydrogen Project, "
            "a major green hydrogen facility in Saudi Arabia. Read More"
        ),
    }

    results = parser.parse(raw_record)
    assert len(results) == 1

    item = results[0]
    assert "NEOM Green Hydrogen Project" in item.projects
    assert item.metadata.get("relationship_candidates")


def test_hydrogen_council_does_not_infer_project_from_company_country_cooccurrence() -> None:
    """
    Company + country + "hydrogen" appearing together must NOT produce a
    fabricated project — only an explicit, known project name does
    (section 5 of the entity-extraction brief).
    """
    parser = HydrogenCouncilParser()
    raw_record = {
        "source_id": "hydrogen_council_newsroom",
        "source_url": "https://hydrogencouncil.com/en/newsroom/",
        "title": "Hydrogen Council Newsroom",
        "text": (
            "Media Release September 10, 2026 "
            "ACWA Power expands hydrogen activity in Saudi Arabia "
            "ACWA Power is expanding its green hydrogen activity across "
            "Saudi Arabia this year. Read More"
        ),
    }

    results = parser.parse(raw_record)
    assert len(results) == 1
    assert results[0].projects == []


# ------------------------------------------------------------
# Hintco: organization extraction, no fabrication
# ------------------------------------------------------------


def test_hintco_extracts_h2global_organisation_mention() -> None:
    parser = HintcoParser()
    raw_record = {
        "source_id": "hintco_news",
        "source_url": "https://hintco.eu/news/",
        "title": "Hintco News",
        "text": (
            "Hintco starts second H2Global tender worth EUR 2.5 billion "
            "Hintco is announcing today the start of the second tender "
            "under the H2Global mechanism. Read more"
        ),
    }

    results = parser.parse(raw_record)
    assert len(results) == 1
    assert "H2Global" in results[0].companies
    assert "Hintco" not in results[0].companies


def test_hintco_lot_pages_never_produce_a_project_mention() -> None:
    """
    Section 7 of the entity-extraction brief: a tender lot is a
    procurement instrument, not a physical project — HintcoParser must
    never populate `projects` from a lot page.
    """
    parser = HintcoParser()
    raw_record = {
        "source_id": "hintco_hpa_auctions",
        "source_url": "https://hintco.eu/hpa-auctions/",
        "title": "Hintco HPA Auctions",
        "text": (
            "Global Lot (GL) Products: Green Ammonia Region: Global "
            "Volume: EUR 900 million Access Tender Platform"
        ),
    }

    results = parser.parse(raw_record)
    assert len(results) >= 1

    for item in results:
        assert item.projects == []


# ------------------------------------------------------------
# Dynamic entity dictionary (section 9) — resolver growth over time
# ------------------------------------------------------------


def test_newly_created_company_becomes_recognizable_in_later_parse(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    # Resolve a brand-new company once (simulating an earlier object
    # whose mention created this canonical entity).
    result = resolve_mention("COMPANY", "Greenko Group")
    assert result.created_new is True

    parser = HydrogenCouncilParser()
    raw_record = {
        "source_id": "hydrogen_council_newsroom",
        "source_url": "https://hydrogencouncil.com/en/newsroom/",
        "title": "Hydrogen Council Newsroom",
        "text": (
            "Media Release September 10, 2026 "
            "Greenko Group joins Hydrogen Council "
            "Greenko Group has joined as a new member. Read More"
        ),
    }

    results = parser.parse(raw_record)
    assert len(results) == 1
    assert "Greenko Group" in results[0].companies


# ------------------------------------------------------------
# Relationship resolution via backfill (section 32, 34, 48)
# ------------------------------------------------------------


def _hc_object_with_relationship() -> IntelligenceObject:
    return IntelligenceObject(
        title="ACWA Power progresses NEOM Green Hydrogen Project",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/neom-project/",
        intelligence_type=IntelligenceType.NEWS,
        companies=["ACWA Power"],
        projects=["NEOM Green Hydrogen Project"],
        metadata={
            "relationship_candidates": [
                {
                    "subject": "ACWA Power",
                    "subject_type": "COMPANY",
                    "relationship_type": "develops",
                    "object": "NEOM Green Hydrogen Project",
                    "object_type": "PROJECT",
                }
            ]
        },
    )


def test_explicit_relationship_resolves_and_persists(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = _hc_object_with_relationship()
    database.save_intelligence_object(obj)

    stats = resolve_mentions_for_object(obj.intelligence_id)
    assert stats["relationships_created"] == 1

    company_entity = database.get_entity_by_normalized_name(
        "COMPANY", "acwa power"
    )
    relationships = database.get_entity_relationships(
        company_entity["entity_id"]
    )
    assert len(relationships) == 1
    assert relationships[0]["relationship_type"] == "develops"
    assert relationships[0]["source_intelligence_object_id"] == (
        obj.intelligence_id
    )


def test_relationship_resolution_is_idempotent(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = _hc_object_with_relationship()
    database.save_intelligence_object(obj)

    first = resolve_mentions_for_object(obj.intelligence_id)
    second = resolve_mentions_for_object(obj.intelligence_id)

    assert first["relationships_created"] == 1
    assert second["relationships_created"] == 0

    company_entity = database.get_entity_by_normalized_name(
        "COMPANY", "acwa power"
    )
    relationships = database.get_entity_relationships(
        company_entity["entity_id"]
    )
    assert len(relationships) == 1


def test_project_country_not_assigned_when_article_mentions_multiple_countries(
    tmp_path, monkeypatch
) -> None:
    """
    Real bug found via live enrichment: an article naming one country per
    (different) new-member company gave no reliable signal for which
    country belongs to which specific project — picking the
    alphabetically-first country produced a wrong real result ("EcoLog
    Terminal Amsterdam" assigned to India). No country must be recorded
    rather than guessing from an ambiguous multi-country article.
    """
    _setup_db(tmp_path, monkeypatch)

    obj = IntelligenceObject(
        title="Six new members join Hydrogen Council",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/six-new-members/",
        intelligence_type=IntelligenceType.NEWS,
        countries=["India", "Japan", "Oman", "Saudi Arabia"],
        projects=["EcoLog Terminal Amsterdam"],
    )
    database.save_intelligence_object(obj)

    resolve_mentions_for_object(obj.intelligence_id)

    entity = database.get_entity_by_normalized_name(
        "PROJECT", "ecolog terminal amsterdam"
    )
    assert entity is not None
    assert entity["country"] is None


def test_project_country_assigned_when_article_mentions_exactly_one(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = IntelligenceObject(
        title="Single-country project article",
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url="https://hydrogencouncil.com/en/single-country/",
        intelligence_type=IntelligenceType.NEWS,
        countries=["Saudi Arabia"],
        projects=["Yanbu Green Hydrogen Hub"],
    )
    database.save_intelligence_object(obj)

    resolve_mentions_for_object(obj.intelligence_id)

    entity = database.get_entity_by_normalized_name(
        "PROJECT", "yanbu green hydrogen hub"
    )
    assert entity is not None
    assert entity["country"] == "Saudi Arabia"


def test_get_entities_with_evidence_excludes_unmentioned_seeded_entities(
    tmp_path, monkeypatch
) -> None:
    """
    A canonical project can exist (from the seed list) with zero real
    mentions — it must not appear in a "with evidence" listing, which is
    what the Projects page uses, so an unmentioned seed entry is never
    shown as if it were real intelligence (section 29).
    """
    _setup_db(tmp_path, monkeypatch)

    from gmip.entities.seed import seed_projects

    seed_projects()
    assert len(database.get_entities("PROJECT")) > 0
    assert database.get_entities_with_evidence("PROJECT") == []

    obj = _hc_object_with_relationship()
    database.save_intelligence_object(obj)
    resolve_mentions_for_object(obj.intelligence_id)

    with_evidence = database.get_entities_with_evidence("PROJECT")
    assert len(with_evidence) == 1
    assert with_evidence[0]["canonical_name"] == "NEOM Green Hydrogen Project"


def test_backfill_twice_does_not_duplicate_relationships(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = _hc_object_with_relationship()
    database.save_intelligence_object(obj)

    run_entity_backfill()
    report = run_entity_backfill()

    assert report["relationships_created"] == 0

    company_entity = database.get_entity_by_normalized_name(
        "COMPANY", "acwa power"
    )
    relationships = database.get_entity_relationships(
        company_entity["entity_id"]
    )
    assert len(relationships) == 1
