"""
EntityResolutionService (section 18 of the entity-resolution brief):
resolves one raw text mention ("ACWA Power", "NGHC") to a canonical
entity. Runs AFTER parsing/persistence, never inside a source parser —
parsers extract facts, resolution happens separately on the already-
persisted IntelligenceObject (see hintco_collector.parse_and_persist_intelligence).

Resolution hierarchy, most to least confident:
  1. exact canonical-name match
  2. exact alias match
  3. normalized-name match (safe formatting-only normalization)
  4. no plausible existing match at all -> create a new canonical entity
  5. a fuzzy-similar existing name -> left UNRESOLVED for manual review

Step 5 is a deliberate dead end: this system never auto-merges a fuzzy
candidate and never auto-creates a duplicate next to it. The brief's own
principle: a false merge is worse than a temporary duplicate.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

import database

from gmip.entities.normalization import (
    normalize_company_name,
    normalize_project_name,
)

NORMALIZERS = {
    "COMPANY": normalize_company_name,
    "PROJECT": normalize_project_name,
}

# Below this similarity, two names are simply unrelated — not even a
# candidate for manual review.
FUZZY_REVIEW_THRESHOLD = 0.82


@dataclass
class ResolutionResult:
    entity_id: str | None
    canonical_name: str | None
    resolution_method: str
    resolution_confidence: float
    created_new: bool = False


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def resolve_mention(
    entity_type: str,
    mention: str,
    country: str | None = None,
) -> ResolutionResult:
    mention = mention.strip()

    if not mention:
        raise ValueError("Cannot resolve an empty mention.")

    normalizer = NORMALIZERS.get(entity_type, normalize_project_name)
    normalized = normalizer(mention)
    mention_casefold = mention.casefold()

    # Steps 1 + 3: both look up by the same normalized_name comparison
    # key (that's what the column stores) — classified as EXACT_CANONICAL
    # only when the mention literally matches the stored display name.
    normalized_match = database.get_entity_by_normalized_name(
        entity_type, normalized
    )

    if normalized_match is not None and entity_type == "PROJECT":
        # Section 13: the same project NAME in a different COUNTRY must
        # never be treated as a safe match — fall through to fuzzy/new
        # handling instead of trusting the normalized-name hit.
        existing_country = normalized_match["country"]

        if country and existing_country and (
            country.casefold() != existing_country.casefold()
        ):
            normalized_match = None

    if normalized_match is not None:
        is_exact = (
            normalized_match["canonical_name"].casefold() == mention_casefold
        )

        return ResolutionResult(
            entity_id=normalized_match["entity_id"],
            canonical_name=normalized_match["canonical_name"],
            resolution_method=(
                "EXACT_CANONICAL" if is_exact else "NORMALIZED_NAME"
            ),
            resolution_confidence=1.0 if is_exact else 0.95,
        )

    # Step 2: exact alias match.
    alias_match = database.get_entity_by_alias(entity_type, mention_casefold)

    if alias_match is not None:
        return ResolutionResult(
            entity_id=alias_match["entity_id"],
            canonical_name=alias_match["canonical_name"],
            resolution_method="EXACT_ALIAS",
            resolution_confidence=1.0,
        )

    # Step 5 pre-check: is there a fuzzy-similar existing entity? If so,
    # this mention stays unresolved rather than risking a false merge or
    # creating a near-duplicate entity.
    existing_entities = database.get_entities(entity_type, limit=1000)
    best_score = 0.0
    best_entity = None

    for candidate in existing_entities:
        score = _similarity(normalized, candidate["normalized_name"])

        if score > best_score:
            best_score = score
            best_entity = candidate

    if best_entity is not None and best_score >= FUZZY_REVIEW_THRESHOLD:
        return ResolutionResult(
            entity_id=None,
            canonical_name=best_entity["canonical_name"],
            resolution_method="FUZZY_UNRESOLVED",
            resolution_confidence=round(best_score, 2),
        )

    # Step 4: no plausible existing match at all — safe to mint a new
    # canonical entity rather than leaving a clearly-novel name
    # unresolved forever.
    entity_id = database.create_entity(
        entity_type=entity_type,
        canonical_name=mention,
        normalized_name=normalized,
        country=country,
    )

    return ResolutionResult(
        entity_id=entity_id,
        canonical_name=mention,
        resolution_method="NEW_ENTITY",
        resolution_confidence=1.0,
        created_new=True,
    )
