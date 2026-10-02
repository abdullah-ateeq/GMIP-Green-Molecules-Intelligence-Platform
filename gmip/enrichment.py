"""
Optional, on-demand full-article-page enrichment for Hydrogen Council.

Root cause this exists to fix (see the entity-extraction brief's audit):
Hydrogen Council's listing-page teaser text is often too short/generic to
name any company or project at all — the real detail lives on each
article's own page. A real example: the "Six new members join Hydrogen
Council" teaser names zero companies; the full article names six
(Acwa, EcoLog, Hydrom, Mitsui O.S.K Lines, TANAKA, 2JCP) and two real
projects (NEOM Green Hydrogen Project, Yanbu Green Hydrogen Hub).

Deliberately a SEPARATE, conservative pass — like
gmip.provenance.recheck_source_availability() — never run automatically
during every normal collection cycle, so it never multiplies requests to
hydrogencouncil.com on every scan. Cloudflare/network failures are
handled per-article exactly like the main collection path
(AccessBlockedError etc.) — one article failing never affects any other,
and never crashes the whole pass.

Re-enriching an already-collected article does not create a duplicate:
the enriched IntelligenceObject reuses the exact same title/source_id as
the original (-> the same identity_key), so
classify_and_save_intelligence_object() correctly classifies it as
UPDATED, consistent with how every other content change in GMIP is
already represented.
"""
from __future__ import annotations

import json
import logging

import database
from hintco_collector import (
    AccessBlockedError,
    download_page_with_browser,
    extract_page_text,
)

from gmip.entities.backfill import resolve_mentions_for_object
from gmip.entities.seed import get_company_candidates, get_project_candidates
from gmip.intelligence.enums import IntelligenceType
from gmip.models.raw_document import RawDocument
from gmip.parsers.base_parser import BaseParser
from gmip.parsers.hydrogen_council_parser import (
    COUNTRY_CANDIDATES,
    PRODUCT_CANDIDATES,
    REGION_CANDIDATES,
)

logger = logging.getLogger(__name__)

# The listing/landing pages themselves — never enrichment targets, only
# the real article pages they link to.
LISTING_PAGE_URLS = {
    "https://hydrogencouncil.com/en/",
    "https://hydrogencouncil.com/en/newsroom/",
    "https://hydrogencouncil.com/en/intelligence/",
    "https://hydrogencouncil.com/en/hydrogen-in-action/",
    "https://hydrogencouncil.com/en/members/",
}


class _EnrichmentParser(BaseParser):
    """
    Not a real source parser (no can_parse()/parse() role in the
    registry) — just a BaseParser instance so this module can reuse
    extract_keywords()/detect_relationships()/build_intelligence_object()
    instead of duplicating them.
    """

    parser_name = "HydrogenCouncilEnrichment"
    source_organisation = "Hydrogen Council"
    source_id = "hydrogen_council"
    default_intelligence_type = IntelligenceType.NEWS

    def can_parse(self, raw_record: dict) -> bool:
        return True

    def parse(self, raw_record: dict) -> list:
        return []


def _candidate_articles(limit: int) -> list[dict]:
    """
    Real Hydrogen Council article records (not the listing pages
    themselves), most-recently-collected first, that haven't already
    been through this enrichment pass.
    """
    rows = database.get_recent_intelligence_objects(
        source_id="hydrogen_council", limit=1000
    )
    candidates = []
    seen_urls: set[str] = set()

    for row in rows:
        url = row["source_url"]

        if url in LISTING_PAGE_URLS or url in seen_urls:
            continue

        # Mark this URL decided either way on its first (most recent,
        # since rows are collected_at DESC) occurrence — an older row
        # for the same URL must never be reconsidered once the newest
        # state (enriched or not) has been read.
        seen_urls.add(url)

        try:
            payload = json.loads(row["payload_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            payload = {}

        if (payload.get("metadata") or {}).get("full_text_enriched"):
            continue

        candidates.append(row)

        if len(candidates) >= limit:
            break

    return candidates


def enrich_hydrogen_council_articles(limit: int = 10) -> dict:
    """
    Fetch each candidate article's real page, re-extract products/
    countries/companies/projects/relationships from the FULL text, and
    persist the enriched version. Returns a summary report.
    """
    helper = _EnrichmentParser()
    # "Hydrogen Council" itself is excluded — every single HC article
    # would otherwise self-tag as mentioning its own publisher, the same
    # exclusion HydrogenCouncilParser already applies to teaser text.
    company_candidates = [
        name for name in get_company_candidates() if name != "Hydrogen Council"
    ]
    project_candidates = get_project_candidates()

    report = {
        "articles_attempted": 0,
        "articles_enriched": 0,
        "articles_blocked": 0,
        "articles_failed": 0,
        "new_company_mentions": 0,
        "new_project_mentions": 0,
        "relationships_created": 0,
    }

    for row in _candidate_articles(limit):
        report["articles_attempted"] += 1
        url = row["source_url"]

        try:
            html = download_page_with_browser(url)
        except AccessBlockedError as exc:
            logger.info("Enrichment blocked for %s: %s", url, exc)
            report["articles_blocked"] += 1
            continue
        except Exception as exc:
            logger.info("Enrichment failed for %s: %s", url, exc)
            report["articles_failed"] += 1
            continue

        _, text = extract_page_text(html)

        if not text:
            report["articles_failed"] += 1
            continue

        raw_document = RawDocument(
            source_id="hydrogen_council",
            source_name="Hydrogen Council",
            source_url=url,
            title=row["title"],
            html=html,
            text=text,
            collector_id="hydrogen_council_enrichment",
            collector_name="HydrogenCouncilEnrichment",
        )
        database.save_raw_document(raw_document)

        companies = helper.extract_keywords(text, company_candidates)
        projects = helper.extract_keywords(text, project_candidates)
        relationships = helper.detect_relationships(text, companies, projects)

        enriched = helper.build_intelligence_object(
            # Same title + source_id as the original -> same identity_key
            # -> classified UPDATED, not a duplicate (section 21 of the
            # entity-extraction brief).
            title=row["title"],
            source_url=url,
            summary=helper.clean_text(text)[:600] or None,
            collector_name="HydrogenCouncilEnrichment",
            intelligence_type=IntelligenceType(row["intelligence_type"]),
            products=helper.extract_keywords(text, PRODUCT_CANDIDATES),
            countries=helper.extract_keywords(text, COUNTRY_CANDIDATES),
            regions=helper.extract_keywords(text, REGION_CANDIDATES),
            companies=companies,
            projects=projects,
            raw_document_id=raw_document.document_id,
            metadata={
                "full_text_enriched": True,
                **(
                    {"relationship_candidates": relationships}
                    if relationships
                    else {}
                ),
            },
        )

        database.classify_and_save_intelligence_object(enriched)
        mention_stats = resolve_mentions_for_object(enriched.intelligence_id)

        report["articles_enriched"] += 1
        report["new_company_mentions"] += len(companies)
        report["new_project_mentions"] += len(projects)
        report["relationships_created"] += mention_stats["relationships_created"]

    return report
