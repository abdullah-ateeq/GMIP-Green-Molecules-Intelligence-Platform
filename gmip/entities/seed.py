"""
Controlled seed set of canonical companies relevant to GMIP's current
sources (section 20-21 of the entity-resolution brief). This is a seed,
not business logic — future entities are created data-driven by the
resolver, not hardcoded here. Aliases are only ones genuinely confirmed
(the brief: "Do not invent aliases").
"""
from __future__ import annotations

# (canonical_name, [confirmed aliases])
COMPANY_SEED: list[tuple[str, list[str]]] = [
    ("ACWA Power", ["ACWA"]),
    ("Air Products", []),
    ("ADNOC", []),
    ("Aramco", ["Saudi Aramco"]),
    ("Masdar", []),
    ("Fertiglobe", []),
    ("Yara", []),
    ("Fortescue", []),
    ("Shell", []),
    ("BP", []),
    ("TotalEnergies", []),
    ("Iberdrola", []),
    ("thyssenkrupp nucera", []),
    ("Nel", []),
    ("Siemens Energy", []),
    ("Plug Power", []),
    ("Cummins", []),
    ("Baker Hughes", []),
    ("NEOM Green Hydrogen Company", ["NGHC"]),
    ("H2Global", ["H2Global Stiftung"]),
    ("Hintco", []),
    ("Hydrogen Council", []),
    # Confirmed from real captured Hydrogen Council report text (see
    # Data/Raw/hydrogen_council_intelligence.txt) — co-authoring/advisory
    # firms that genuinely appear in collected content, not invented.
    ("McKinsey & Company", ["McKinsey"]),
    ("Wood plc", []),
    ("Baringa", []),
]

# Flat canonical-name list for parser-level extract_keywords() candidates
# (section 39 of the entity-resolution brief: conservative, deterministic
# keyword matching, not a capitalized-phrase guesser). One shared list so
# every parser recognizes the same companies instead of maintaining N
# near-duplicate candidate lists.
COMPANY_NAME_CANDIDATES: list[str] = [name for name, _ in COMPANY_SEED]

# A small, genuinely well-known set of named green hydrogen/ammonia
# projects — kept deliberately short. This is a seed to extract FROM,
# not a claim that these projects are currently active in GMIP's
# collected data; a project only becomes a canonical entity once a
# parser actually finds its name mentioned in real text (section 18:
# "do not automatically create a Project entity from any capitalized
# phrase... only when an explicit project name exists").
PROJECT_SEED: list[tuple[str, list[str]]] = [
    ("NEOM Green Hydrogen Project", ["NGHC Project"]),
    ("HyDeal Ambition", []),
]

PROJECT_NAME_CANDIDATES: list[str] = [name for name, _ in PROJECT_SEED]


def _flatten_with_aliases(seed: list[tuple[str, list[str]]]) -> list[str]:
    names: list[str] = []

    for canonical_name, aliases in seed:
        names.append(canonical_name)
        names.extend(aliases)

    return names


def get_company_candidates() -> list[str]:
    """
    Parser-facing extraction candidates: the seed list's canonical names
    AND aliases (so a bare "NGHC" in body text is recognized, not just
    the full "NEOM Green Hydrogen Company"), plus any canonical company
    already in the database that isn't in the seed — so a company
    created later via NEW_ENTITY resolution becomes recognizable in
    future parsing too (section 9 of the entity-extraction brief: build
    the matcher from existing canonical entities, not only a static
    list). Falls back to the static seed alone if the database isn't
    reachable, so parsing never breaks on this.
    """
    candidates = set(_flatten_with_aliases(COMPANY_SEED))

    try:
        import database

        for entity in database.get_entities("COMPANY", limit=1000):
            candidates.add(entity["canonical_name"])

            import json

            try:
                candidates.update(json.loads(entity["aliases_json"] or "[]"))
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    return sorted(candidates, key=len, reverse=True)


def get_project_candidates() -> list[str]:
    """Project equivalent of get_company_candidates(); see its docstring."""
    candidates = set(_flatten_with_aliases(PROJECT_SEED))

    try:
        import database

        for entity in database.get_entities("PROJECT", limit=1000):
            candidates.add(entity["canonical_name"])

            import json

            try:
                candidates.update(json.loads(entity["aliases_json"] or "[]"))
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    return sorted(candidates, key=len, reverse=True)


def seed_companies() -> int:
    """
    Idempotent: only creates an entity that doesn't already resolve by
    exact name. Safe to call on every backfill run.
    """
    import database

    from gmip.entities.normalization import normalize_company_name

    created = 0

    for canonical_name, aliases in COMPANY_SEED:
        existing = database.get_entity_by_normalized_name(
            "COMPANY", normalize_company_name(canonical_name)
        )

        if existing is None:
            entity_id = database.create_entity(
                entity_type="COMPANY",
                canonical_name=canonical_name,
                normalized_name=normalize_company_name(canonical_name),
                aliases=aliases,
            )
            created += 1
        else:
            entity_id = existing["entity_id"]

        for alias in aliases:
            database.add_entity_alias(entity_id, alias)

    return created


def seed_projects() -> int:
    """Project equivalent of seed_companies(); see its docstring."""
    import database

    from gmip.entities.normalization import normalize_project_name

    created = 0

    for canonical_name, aliases in PROJECT_SEED:
        existing = database.get_entity_by_normalized_name(
            "PROJECT", normalize_project_name(canonical_name)
        )

        if existing is None:
            entity_id = database.create_entity(
                entity_type="PROJECT",
                canonical_name=canonical_name,
                normalized_name=normalize_project_name(canonical_name),
                aliases=aliases,
            )
            created += 1
        else:
            entity_id = existing["entity_id"]

        for alias in aliases:
            database.add_entity_alias(entity_id, alias)

    return created
