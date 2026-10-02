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
from gmip.entities.seed import seed_companies, seed_projects


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
        "relationships_created": 0,
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

    # mention text -> resolved entity_id, so relationship candidates
    # (subject/object given as raw mention text) can be mapped to real
    # entity_ids below without re-resolving.
    resolved_companies: dict[str, str] = {}
    resolved_projects: dict[str, str] = {}

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
        else:
            resolved_companies[mention] = result.entity_id

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
        else:
            resolved_projects[mention] = result.entity_id

    # Relationships (section 14-16 of the entity-extraction brief): only
    # created when BOTH sides already resolved to a real canonical entity
    # from THIS object's own mentions — never invented from co-occurrence
    # alone, and never pointed at an entity this object didn't actually
    # mention.
    relationship_candidates = (
        payload.get("metadata", {}).get("relationship_candidates") or []
    )
    entity_maps = {"COMPANY": resolved_companies, "PROJECT": resolved_projects}

    for candidate in relationship_candidates:
        subject_map = entity_maps.get(candidate.get("subject_type", ""))
        object_map = entity_maps.get(candidate.get("object_type", ""))

        if subject_map is None or object_map is None:
            continue

        subject_entity_id = subject_map.get(candidate.get("subject", ""))
        object_entity_id = object_map.get(candidate.get("object", ""))

        if not subject_entity_id or not object_entity_id:
            continue

        created = database.save_entity_relationship(
            subject_entity_id=subject_entity_id,
            relationship_type=candidate["relationship_type"],
            object_entity_id=object_entity_id,
            source_intelligence_object_id=intelligence_object_id,
            confidence=0.9,
        )

        if created:
            stats["relationships_created"] += 1

    return stats


def run_entity_backfill(limit: int | None = None) -> dict:
    """
    Resolve entities for every persisted IntelligenceObject. Returns the
    data-quality report described in section 52 of the entity-resolution
    brief.
    """
    companies_seeded = seed_companies()
    projects_seeded = seed_projects()

    rows = database.get_recent_intelligence_objects(
        limit=limit or 100000
    )

    report = {
        "objects_processed": 0,
        "companies_seeded": companies_seeded,
        "projects_seeded": projects_seeded,
        "company_mentions": 0,
        "companies_created": 0,
        "company_mentions_unresolved": 0,
        "project_mentions": 0,
        "projects_created": 0,
        "project_mentions_unresolved": 0,
        "relationships_created": 0,
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
            "relationships_created",
        ):
            report[key] += object_stats[key]

    report["canonical_companies"] = len(database.get_entities("COMPANY", limit=10000))
    report["canonical_projects"] = len(database.get_entities("PROJECT", limit=10000))
    report["possible_duplicates"] = len(
        database.get_unresolved_mentions(limit=10000)
    )

    return report
