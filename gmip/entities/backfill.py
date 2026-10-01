"""
Entity-resolution backfill (section 43 of the entity-resolution brief):
runs resolution against already-persisted IntelligenceObjects. Does not
recollect or reparse anything — reads the existing `companies`/`projects`
string lists already on each object and resolves each mention.

Idempotent (section 48): entity_mentions has a UNIQUE(intelligence_object_id,
entity_type, original_mention) constraint, so re-running never creates a
duplicate mention row, and entity creation is naturally idempotent via
the EXACT_CANONICAL/NORMALIZED_NAME lookup path in resolve_mention().
"""
from __future__ import annotations

import json

import database

from gmip.entities.resolver import resolve_mention
from gmip.entities.seed import seed_companies


def resolve_mentions_for_object(intelligence_object_id: str) -> dict:
    """
    Resolve every company/project mention on one already-persisted
    IntelligenceObject. Returns per-object counts, used by both the
    backfill pass and the live post-persistence hook (see
    hintco_collector.parse_and_persist_intelligence).
    """
    with database.get_connection() as connection:
        row = connection.execute(
            "SELECT companies, countries, payload_json "
            "FROM intelligence_objects WHERE intelligence_id = ?",
            (intelligence_object_id,),
        ).fetchone()

    stats = {
        "company_mentions": 0,
        "companies_created": 0,
        "company_mentions_unresolved": 0,
        "project_mentions": 0,
        "projects_created": 0,
        "project_mentions_unresolved": 0,
    }

    if row is None:
        return stats

    try:
        companies = json.loads(row["companies"] or "[]")
    except (json.JSONDecodeError, TypeError):
        companies = []

    try:
        countries = json.loads(row["countries"] or "[]")
    except (json.JSONDecodeError, TypeError):
        countries = []

    try:
        payload = json.loads(row["payload_json"] or "{}")
    except (json.JSONDecodeError, TypeError):
        payload = {}

    projects = payload.get("projects") or []
    country_context = countries[0] if countries else None

    for mention in companies:
        result = resolve_mention("COMPANY", mention)
        database.save_entity_mention(
            intelligence_object_id=intelligence_object_id,
            entity_id=result.entity_id,
            entity_type="COMPANY",
            original_mention=mention,
            resolution_method=result.resolution_method,
            resolution_confidence=result.resolution_confidence,
        )
        stats["company_mentions"] += 1

        if result.created_new:
            stats["companies_created"] += 1

        if result.entity_id is None:
            stats["company_mentions_unresolved"] += 1

    for mention in projects:
        result = resolve_mention("PROJECT", mention, country=country_context)
        database.save_entity_mention(
            intelligence_object_id=intelligence_object_id,
            entity_id=result.entity_id,
            entity_type="PROJECT",
            original_mention=mention,
            resolution_method=result.resolution_method,
            resolution_confidence=result.resolution_confidence,
        )
        stats["project_mentions"] += 1

        if result.created_new:
            stats["projects_created"] += 1

        if result.entity_id is None:
            stats["project_mentions_unresolved"] += 1

    return stats


def run_entity_backfill(limit: int | None = None) -> dict:
    """
    Resolve entities for every persisted IntelligenceObject. Returns the
    data-quality report described in section 52 of the entity-resolution
    brief.
    """
    companies_seeded = seed_companies()

    rows = database.get_recent_intelligence_objects(
        limit=limit or 100000
    )

    report = {
        "objects_processed": 0,
        "companies_seeded": companies_seeded,
        "company_mentions": 0,
        "companies_created": 0,
        "company_mentions_unresolved": 0,
        "project_mentions": 0,
        "projects_created": 0,
        "project_mentions_unresolved": 0,
    }

    for row in rows:
        object_stats = resolve_mentions_for_object(row["intelligence_id"])
        report["objects_processed"] += 1

        for key in (
            "company_mentions",
            "companies_created",
            "company_mentions_unresolved",
            "project_mentions",
            "projects_created",
            "project_mentions_unresolved",
        ):
            report[key] += object_stats[key]

    report["canonical_companies"] = len(database.get_entities("COMPANY", limit=10000))
    report["canonical_projects"] = len(database.get_entities("PROJECT", limit=10000))
    report["possible_duplicates"] = len(
        database.get_unresolved_mentions(limit=10000)
    )

    return report
