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
]


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
