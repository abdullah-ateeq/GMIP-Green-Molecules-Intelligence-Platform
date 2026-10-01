from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402
from gmip.entities.backfill import (  # noqa: E402
    resolve_mentions_for_object,
    run_entity_backfill,
)
from gmip.entities.normalization import (  # noqa: E402
    normalize_company_name,
    normalize_project_name,
)
from gmip.entities.resolver import resolve_mention  # noqa: E402
from gmip.entities.seed import seed_companies  # noqa: E402
from gmip.intelligence.enums import IntelligenceType  # noqa: E402
from gmip.intelligence.intelligence_object import IntelligenceObject  # noqa: E402


def _setup_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()


# ------------------------------------------------------------
# Normalization (section 7)
# ------------------------------------------------------------


def test_company_normalization_matches_formatting_variants() -> None:
    assert normalize_company_name("ACWA Power") == normalize_company_name(
        "ACWA POWER"
    )
    assert normalize_company_name("ACWA Power") == normalize_company_name(
        "Acwa Power"
    )
    assert normalize_company_name("ACWA Power") == normalize_company_name(
        "ACWA Power Company"
    )
    assert normalize_company_name("ACWA Power") == normalize_company_name(
        "ACWA Power International"
    )


def test_company_normalization_never_does_substring_merging() -> None:
    """
    "Total" must never normalize the same as "TotalEnergies" — no
    substring/contains matching (section 7 of the entity-resolution
    brief, explicit example).
    """
    assert normalize_company_name("Total") != normalize_company_name(
        "TotalEnergies"
    )
    assert normalize_company_name("Air Products") != normalize_company_name(
        "Air Products Qudra"
    )


# ------------------------------------------------------------
# Company resolution (section 45)
# ------------------------------------------------------------


def test_formatting_variants_resolve_to_same_company(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    first = resolve_mention("COMPANY", "ACWA Power")
    second = resolve_mention("COMPANY", "ACWA POWER")
    third = resolve_mention("COMPANY", "Acwa Power")

    assert first.created_new is True
    assert second.entity_id == first.entity_id
    assert third.entity_id == first.entity_id
    assert second.resolution_method in {"EXACT_CANONICAL", "NORMALIZED_NAME"}


def test_seeded_alias_resolves_to_canonical_company(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)
    seed_companies()

    result = resolve_mention("COMPANY", "NGHC")

    assert result.resolution_method == "EXACT_ALIAS"
    assert result.canonical_name == "NEOM Green Hydrogen Company"
    assert result.resolution_confidence == 1.0


def test_similar_but_distinct_companies_are_not_auto_merged(
    tmp_path, monkeypatch
) -> None:
    """
    "Air Products" and "Air Products Qudra" may be related but are not
    necessarily the same legal entity — must stay unresolved, not merged
    (section 10 of the entity-resolution brief).
    """
    _setup_db(tmp_path, monkeypatch)

    base = resolve_mention("COMPANY", "Air Products")
    related = resolve_mention("COMPANY", "Air Products Qudra")

    assert base.created_new is True
    # Either a brand-new distinct entity, or flagged unresolved for
    # review — but never silently pointed at the same entity_id as
    # "Air Products" without a human confirming it.
    if related.entity_id is not None:
        assert related.entity_id != base.entity_id
    else:
        assert related.resolution_method == "FUZZY_UNRESOLVED"


def test_unrelated_new_company_creates_a_new_entity(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    result = resolve_mention("COMPANY", "Baker Hughes")

    assert result.created_new is True
    assert result.resolution_method == "NEW_ENTITY"


# ------------------------------------------------------------
# Project resolution (section 46)
# ------------------------------------------------------------


def test_same_project_name_same_country_resolves(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)

    first = resolve_mention(
        "PROJECT", "NEOM Green Hydrogen Project", country="Saudi Arabia"
    )
    second = resolve_mention(
        "PROJECT", "NEOM Green Hydrogen Project", country="Saudi Arabia"
    )

    assert second.entity_id == first.entity_id


def test_same_project_name_different_country_not_merged(
    tmp_path, monkeypatch
) -> None:
    """
    Section 13's explicit requirement: identical project names in
    different countries must NOT resolve to the same canonical project.
    """
    _setup_db(tmp_path, monkeypatch)

    first = resolve_mention(
        "PROJECT", "Green Hydrogen Project", country="Germany"
    )
    second = resolve_mention(
        "PROJECT", "Green Hydrogen Project", country="Oman"
    )

    assert second.entity_id != first.entity_id


# ------------------------------------------------------------
# Relationships (section 47) — only created from explicit signal
# ------------------------------------------------------------


def test_relationship_requires_explicit_creation_not_co_mention(
    tmp_path, monkeypatch
) -> None:
    """
    Nothing in this phase auto-infers a relationship from two entities
    merely co-occurring in the same article — save_entity_relationship()
    must be called explicitly with real evidence. This test documents
    that guarantee: resolving two mentions in the same object does not,
    by itself, create any relationship row.
    """
    _setup_db(tmp_path, monkeypatch)

    company = resolve_mention("COMPANY", "ACWA Power")
    project = resolve_mention("PROJECT", "NEOM Green Hydrogen Project")

    relationships = database.get_entity_relationships(company.entity_id)
    assert relationships == []

    relationships = database.get_entity_relationships(project.entity_id)
    assert relationships == []


def test_explicit_relationship_can_be_recorded_with_evidence(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    company = resolve_mention("COMPANY", "ACWA Power")
    project = resolve_mention("PROJECT", "NEOM Green Hydrogen Project")

    created = database.save_entity_relationship(
        subject_entity_id=company.entity_id,
        relationship_type="develops",
        object_entity_id=project.entity_id,
        source_intelligence_object_id="some-intelligence-id",
        confidence=0.9,
    )

    assert created is True

    relationships = database.get_entity_relationships(company.entity_id)
    assert len(relationships) == 1
    assert relationships[0]["relationship_type"] == "develops"


# ------------------------------------------------------------
# Backfill (section 48) — idempotency
# ------------------------------------------------------------


def _make_object(title: str, companies: list[str]) -> IntelligenceObject:
    return IntelligenceObject(
        title=title,
        source_organisation="Hydrogen Council",
        source_id="hydrogen_council",
        source_url=f"https://hydrogencouncil.com/en/{title.lower().replace(' ', '-')}/",
        intelligence_type=IntelligenceType.NEWS,
        companies=companies,
    )


def test_resolve_mentions_for_object_creates_mentions(
    tmp_path, monkeypatch
) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = _make_object("ACWA Power news", ["ACWA Power"])
    database.save_intelligence_object(obj)

    stats = resolve_mentions_for_object(obj.intelligence_id)

    assert stats["company_mentions"] == 1
    assert stats["companies_created"] == 1

    mentions = database.get_entity_mentions(
        database.get_entity_by_normalized_name(
            "COMPANY", normalize_company_name("ACWA Power")
        )["entity_id"]
    )
    assert len(mentions) == 1
    assert mentions[0]["title"] == "ACWA Power news"


def test_backfill_is_idempotent(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)

    obj = _make_object("ACWA Power news", ["ACWA Power", "Baker Hughes"])
    database.save_intelligence_object(obj)

    first_report = run_entity_backfill()
    second_report = run_entity_backfill()

    assert first_report["canonical_companies"] == second_report["canonical_companies"]
    assert second_report["companies_created"] == 0  # all already existed

    mentions = database.get_entity_mentions(
        database.get_entity_by_normalized_name(
            "COMPANY", normalize_company_name("ACWA Power")
        )["entity_id"]
    )
    assert len(mentions) == 1  # not duplicated by the second run


def test_backfill_report_is_honest_about_empty_project_data(
    tmp_path, monkeypatch
) -> None:
    """
    No parser currently extracts `projects` — backfill against such data
    must report zero canonical projects, never fabricate one.
    """
    _setup_db(tmp_path, monkeypatch)

    obj = _make_object("A plain article", [])
    database.save_intelligence_object(obj)

    report = run_entity_backfill()

    assert report["canonical_projects"] == 0
    assert report["project_mentions"] == 0


# ------------------------------------------------------------
# Search (section 49)
# ------------------------------------------------------------


def test_search_by_canonical_name(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    seed_companies()

    results = database.search_entities("ACWA Power", entity_type="COMPANY")

    assert any(r["canonical_name"] == "ACWA Power" for r in results)


def test_search_by_alias_finds_canonical_entity(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    seed_companies()

    results = database.search_entities("NGHC", entity_type="COMPANY")

    assert len(results) == 1
    assert results[0]["canonical_name"] == "NEOM Green Hydrogen Company"


# ------------------------------------------------------------
# Merge (section 34)
# ------------------------------------------------------------


def test_merge_moves_mentions_and_aliases(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)

    duplicate = resolve_mention("COMPANY", "Air Products Qudra")
    canonical = resolve_mention("COMPANY", "Air Products")

    obj = _make_object("Air Products Qudra news", ["Air Products Qudra"])
    database.save_intelligence_object(obj)
    resolve_mentions_for_object(obj.intelligence_id)

    database.merge_entities(
        duplicate.entity_id, canonical.entity_id, reason="confirmed same entity"
    )

    assert database.get_entity(duplicate.entity_id) is None

    mentions = database.get_entity_mentions(canonical.entity_id)
    assert any(m["intelligence_object_id"] == obj.intelligence_id for m in mentions)

    merged_entity = database.get_entity(canonical.entity_id)
    import json

    aliases = json.loads(merged_entity["aliases_json"])
    assert "Air Products Qudra" in aliases
