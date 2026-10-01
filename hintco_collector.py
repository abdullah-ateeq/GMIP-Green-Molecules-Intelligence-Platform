from __future__ import annotations

import hashlib
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from config import (
    CHANGES_DIR,
    EVENT_KEYWORDS,
    HINTCO_SOURCES,
    PRODUCT_KEYWORDS,
    RAW_DIR,
    SNAPSHOT_DIR,
    SUPPLY_KEYWORDS,
)

from database import (
    classify_and_save_intelligence_object,
    get_snapshot,
    insert_change,
    insert_initial_snapshot,
    save_raw_document,
    update_snapshot,
)

from models import CollectionResult
from gmip.entities.backfill import resolve_mentions_for_object
from gmip.models.raw_document import RawDocument
from gmip.parsers import build_default_registry

# Built once at import time. Routes each source_id to its structured
# parser (see gmip.parsers.build_default_registry). Parsing happens
# alongside the legacy snapshot/change pipeline below, never in place of
# it, and any parser failure is swallowed so it can never break collection.
_PARSER_REGISTRY = build_default_registry()


# ==========================================================
# TEXT UTILITIES
# ==========================================================

def clean_text(text: str) -> str:
    """
    Remove duplicate spaces and invisible characters.
    """

    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def calculate_hash(text: str) -> str:
    """
    Calculate SHA256 hash.
    """

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def safe_filename(name: str) -> str:
    """
    Convert a string into a valid Windows filename.
    """

    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", "_", name)

    return name.strip("_")


# ==========================================================
# PAGE VALIDATION
# ==========================================================

class AccessBlockedError(RuntimeError):
    """
    Raised specifically when a bot-detection/access-control challenge
    (e.g. Cloudflare) rejects a page — distinct from a plain HTTP error
    or short/malformed content, so callers can classify this case as
    BLOCKED_BY_ACCESS_CONTROL rather than a generic processing failure
    or (incorrectly) a broken collector/parser implementation.
    """


def validate_downloaded_page(
    url: str,
    html: str,
    status_code: int | None,
) -> None:
    """
    Reject HTTP error pages, Cloudflare challenges, and other
    invalid responses before they can become database snapshots.
    """

    lowered_html = html.lower()

    cloudflare_markers = [
        "<title>just a moment...</title>",
        "challenges.cloudflare.com",
        "cf-browser-verification",
        "cf-chl-",
        "challenge-platform",
        "checking your browser",
        "verify you are human",
        "enable javascript and cookies to continue",
    ]

    detected_markers = [
        marker
        for marker in cloudflare_markers
        if marker in lowered_html
    ]

    if status_code is not None and status_code >= 400:
        raise RuntimeError(
            f"Source returned HTTP {status_code}: {url}. "
            "The page was rejected and was not saved."
        )

    if detected_markers:
        raise AccessBlockedError(
            "Cloudflare challenge page detected for "
            f"{url}. The page was rejected and was not saved. "
            f"Detected marker: {detected_markers[0]}"
        )

    if len(html.strip()) < 200:
        raise RuntimeError(
            f"Downloaded HTML from {url} is unexpectedly short."
        )


# ==========================================================
# PLAYWRIGHT DOWNLOADER
# ==========================================================

def download_page_with_browser(url: str) -> str:
    """
    Download a webpage using Chromium.

    The browser response is validated before the HTML is returned.
    HTTP error pages and Cloudflare challenge pages are rejected so
    they cannot be saved as source snapshots.
    """

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True,
        )

        context = browser.new_context(
            viewport={
                "width": 1600,
                "height": 1200,
            },
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        page = context.new_page()

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(5000)

            html = page.content()

            status_code = (
                response.status
                if response is not None
                else None
            )

            print("=" * 80)
            print(f"URL: {url}")
            print(f"Initial Status: {status_code}")

            validate_downloaded_page(
                url=url,
                html=html,
                status_code=status_code,
            )

            print(
                "Page validation passed. "
                f"Downloaded HTML length: {len(html):,}"
            )
            print("=" * 80)

            return html

        finally:
            context.close()
            browser.close()


# ==========================================================
# HTML EXTRACTION
# ==========================================================

def extract_page_text(html: str) -> tuple[str, str]:

    soup = BeautifulSoup(
        html,
        "lxml",
    )

    title = (
        clean_text(
            soup.title.get_text()
        )
        if soup.title
        else "Untitled"
    )

    for tag in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "iframe",
            "form",
        ]
    ):
        tag.decompose()

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.body
        or soup
    )

    text = clean_text(
        main.get_text(
            separator=" ",
            strip=True,
        )
    )

    return title, text


# ==========================================================
# PRODUCT DETECTION
# ==========================================================

def detect_products(text: str) -> list[str]:

    lowered = text.lower()

    detected = []

    for product, keywords in PRODUCT_KEYWORDS.items():

        for keyword in keywords:

            if keyword in lowered:

                detected.append(product)
                break

    return detected


# ==========================================================
# EVENT DETECTION
# ==========================================================

def detect_event_types(text: str) -> list[str]:

    lowered = text.lower()

    detected = []

    for event, keywords in EVENT_KEYWORDS.items():

        for keyword in keywords:

            if keyword in lowered:

                detected.append(event)
                break

    return detected


# ==========================================================
# RELEVANCE DETECTION
# ==========================================================

def determine_relevance(
    text: str,
    products: list[str],
) -> bool:

    lowered = text.lower()

    has_product = len(products) > 0

    has_supply = any(
        keyword in lowered
        for keyword in SUPPLY_KEYWORDS
    )

    return has_product and has_supply


# ==========================================================
# FETCH PAGE
# ==========================================================

def fetch_page(source: dict) -> RawDocument:
    """
    Download one source and return its raw collected content.

    This function performs collection only. It does not determine
    products, event types, relevance, entities, or intelligence.
    """

    html = download_page_with_browser(
        source["url"]
    )

    title, extracted_text = extract_page_text(
        html
    )

    if not extracted_text:
        raise RuntimeError(
            f"No readable text extracted from {source['url']}"
        )

    raw_html_path = (
        RAW_DIR
        / f"{safe_filename(source['source_id'])}.html"
    )

    raw_text_path = (
        RAW_DIR
        / f"{safe_filename(source['source_id'])}.txt"
    )

    raw_html_path.write_text(
        html,
        encoding="utf-8",
    )

    raw_text_path.write_text(
        extracted_text,
        encoding="utf-8",
    )

    return RawDocument(
        source_id=source["source_id"],
        source_name=source["source_name"],
        source_url=source["url"],
        title=title,
        html=html,
        text=extracted_text,
        status="SUCCESS",
        content_type="text/html",
        language=source.get("language", "en"),
        collector_id=source.get(
            "collector_id",
            "website_collector",
        ),
        collector_name=source.get(
            "collector_name",
            "GMIP Website Collector",
        ),
        # Preserve the legacy extracted-text hash during migration so
        # existing snapshots are not incorrectly marked as changed.
        content_hash=calculate_hash(extracted_text),
        metadata={
            "source_type": source.get("source_type"),
            "raw_html_path": str(raw_html_path),
            "raw_text_path": str(raw_text_path),
        },
    )

# ==========================================================
# SENTENCE SPLITTING
# ==========================================================

def split_into_sentences(text: str) -> list[str]:
    """
    Split extracted page text into readable sentences.

    Very short fragments are ignored because website menus,
    headers and navigation labels often create noise.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    cleaned_sentences: list[str] = []

    for sentence in sentences:

        sentence = clean_text(sentence)

        if len(sentence) >= 25:
            cleaned_sentences.append(sentence)

    return cleaned_sentences


# ==========================================================
# CHANGE SUMMARY
# ==========================================================

def create_change_summary(
    old_text: str,
    new_text: str,
) -> str:
    """
    Compare the previous and current page text and produce
    a readable summary of added and removed content.
    """

    old_sentences = split_into_sentences(
        old_text
    )

    new_sentences = split_into_sentences(
        new_text
    )

    old_sentence_set = set(
        old_sentences
    )

    new_sentence_set = set(
        new_sentences
    )

    added_sentences = [
        sentence
        for sentence in new_sentences
        if sentence not in old_sentence_set
    ]

    removed_sentences = [
        sentence
        for sentence in old_sentences
        if sentence not in new_sentence_set
    ]

    summary_parts: list[str] = []

    if added_sentences:

        added_preview = " | ".join(
            added_sentences[:5]
        )

        summary_parts.append(
            f"Added: {added_preview}"
        )

    if removed_sentences:

        removed_preview = " | ".join(
            removed_sentences[:5]
        )

        summary_parts.append(
            f"Removed: {removed_preview}"
        )

    if summary_parts:

        return " || ".join(
            summary_parts
        )

    similarity_ratio = SequenceMatcher(
        None,
        old_text,
        new_text,
    ).ratio()

    return (
        "The source page content changed, but no clear "
        "sentence-level addition or removal was identified. "
        f"Text similarity with the previous version: "
        f"{similarity_ratio:.2%}."
    )


# ==========================================================
# SAVE SNAPSHOT
# ==========================================================

def save_snapshot_file(
    source_id: str,
    content: str,
) -> Path:
    """
    Save a timestamped copy of the extracted page text.
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    snapshot_filename = (
        f"{safe_filename(source_id)}_"
        f"{timestamp}.txt"
    )

    snapshot_path = (
        SNAPSHOT_DIR
        / snapshot_filename
    )

    snapshot_path.write_text(
        content,
        encoding="utf-8",
    )

    return snapshot_path


# ==========================================================
# SAVE CHANGE REPORT
# ==========================================================

def save_change_report(
    source_id: str,
    source_name: str,
    source_url: str,
    old_text: str,
    new_text: str,
    change_summary: str,
    products: list[str],
    event_types: list[str],
) -> Path:
    """
    Save a human-readable report whenever a monitored
    Hintco page changes.
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_filename = (
        f"{safe_filename(source_id)}_"
        f"{timestamp}_change.txt"
    )

    report_path = (
        CHANGES_DIR
        / report_filename
    )

    products_text = (
        ", ".join(products)
        if products
        else "None"
    )

    events_text = (
        ", ".join(event_types)
        if event_types
        else "None"
    )

    report_content = f"""
HINTCO SOURCE CHANGE REPORT
============================================================

Source:
{source_name}

Official URL:
{source_url}

Detected At:
{datetime.now().isoformat(timespec="seconds")}

Detected Products:
{products_text}

Detected Event Types:
{events_text}

Change Summary:
{change_summary}

============================================================
PREVIOUS CONTENT
============================================================

{old_text}

============================================================
CURRENT CONTENT
============================================================

{new_text}
""".strip()

    report_path.write_text(
        report_content,
        encoding="utf-8",
    )

    return report_path


# ==========================================================
# PROCESS ONE SOURCE
# ==========================================================

def parse_and_persist_intelligence(
    raw_document: RawDocument,
) -> dict:
    """
    Best-effort structured parsing for one RawDocument, from any collector.

    Public and reused across collectors (Hintco's own process_source()
    below, and the H2 View legacy adapter in collectors/h2_view_collector.py)
    so parsing/persistence logic lives in exactly one place. Persists the
    RawDocument as an audit-trail row, looks up a real parser for this
    page's source_id via the shared ParserRegistry, parses the RawDocument
    into IntelligenceObjects, and persists each with item-level NEW/UPDATED/
    UNCHANGED change detection (see database.classify_and_save_intelligence_object).
    Any failure here is logged and swallowed — it must never affect the
    caller's own collection/snapshot logic.

    Returns a small summary dict (for the end-to-end runner to log):
    {"source_id", "parser", "objects_parsed", "new", "updated",
    "unchanged", "error"}.
    """

    summary = {
        "source_id": raw_document.source_id,
        "parser": None,
        "objects_parsed": 0,
        "new": 0,
        "updated": 0,
        "unchanged": 0,
        "error": None,
    }

    try:
        save_raw_document(raw_document)

        parser = _PARSER_REGISTRY.get_parser(raw_document.source_id)

        if parser is None:
            return summary

        summary["parser"] = parser.parser_name

        intelligence_objects = parser.parse_many(
            [raw_document.to_dict()],
            skip_invalid=True,
        )
        summary["objects_parsed"] = len(intelligence_objects)

        for intelligence_object in intelligence_objects:
            intelligence_object.raw_document_id = raw_document.document_id

            result = classify_and_save_intelligence_object(
                intelligence_object
            )

            # Entity resolution runs after persistence, on the already-
            # saved object (section 19 of the entity-resolution brief) —
            # never inside the parser itself. A resolution failure must
            # never break collection, so it stays inside this same
            # try/except as the rest of structured parsing.
            resolve_mentions_for_object(intelligence_object.intelligence_id)

            if result["change_type"] == "NEW":
                summary["new"] += 1
            elif result["change_type"] == "UPDATED":
                summary["updated"] += 1
                print(
                    f"  UPDATED: {intelligence_object.title} "
                    f"({raw_document.source_id}) — {result['diff']}"
                )
            else:
                summary["unchanged"] += 1

    except Exception as exc:
        summary["error"] = str(exc)
        print(
            f"Structured parsing failed for {raw_document.source_id} "
            f"(legacy collection continues): {exc}"
        )

    return summary


def process_source(
    source: dict,
) -> CollectionResult:
    """
    Collect one website source, compare its raw document with the
    previous database snapshot, and return an operational summary.

    Product, event, and relevance detection remain here temporarily
    until they are moved into the dedicated parser layer.
    """

    raw_document = fetch_page(
        source
    )

    parse_and_persist_intelligence(raw_document)

    document_text = raw_document.text or ""

    # Temporary legacy analysis. These calls will move into the
    # parser layer after the RawDocument migration is verified.
    products = detect_products(
        document_text
    )

    event_types = detect_event_types(
        document_text
    )

    is_relevant = determine_relevance(
        document_text,
        products,
    )

    existing_snapshot = get_snapshot(
        raw_document.source_id
    )

    products_text = ", ".join(
        products
    )

    events_text = ", ".join(
        event_types
    )

    source_type = (
        raw_document.metadata.get("source_type")
        or "website"
    )

    # ------------------------------------------------------
    # FIRST SUCCESSFUL RUN FOR THIS SOURCE
    # ------------------------------------------------------

    if existing_snapshot is None:

        insert_initial_snapshot(
            source_id=raw_document.source_id,
            source_name=raw_document.source_name,
            source_url=raw_document.source_url,
            source_type=source_type,
            page_title=raw_document.title or "Untitled",
            content_hash=raw_document.content_hash or "",
            extracted_text=document_text,
            detected_products=products_text,
            detected_event_types=events_text,
            is_relevant=is_relevant,
        )

        snapshot_path = save_snapshot_file(
            source_id=raw_document.source_id,
            content=document_text,
        )

        return CollectionResult(
            source_id=raw_document.source_id,
            source_name=raw_document.source_name,
            source_url=raw_document.source_url,
            status="INITIAL_SNAPSHOT",
            relevant=is_relevant,
            products=products,
            event_types=event_types,
            message=(
                "Initial baseline snapshot created. "
                f"Snapshot saved to: {snapshot_path}"
            ),
        )

    # ------------------------------------------------------
    # PREVIOUS SNAPSHOT EXISTS
    # ------------------------------------------------------

    old_hash = (
        existing_snapshot["content_hash"]
    )

    old_text = (
        existing_snapshot["extracted_text"]
        or ""
    )

    page_changed = (
        old_hash != raw_document.content_hash
    )

    # ------------------------------------------------------
    # NO CHANGE
    # ------------------------------------------------------

    if not page_changed:

        update_snapshot(
            source_id=raw_document.source_id,
            source_name=raw_document.source_name,
            source_url=raw_document.source_url,
            source_type=source_type,
            page_title=raw_document.title or "Untitled",
            content_hash=raw_document.content_hash or "",
            extracted_text=document_text,
            detected_products=products_text,
            detected_event_types=events_text,
            is_relevant=is_relevant,
            changed=False,
        )

        return CollectionResult(
            source_id=raw_document.source_id,
            source_name=raw_document.source_name,
            source_url=raw_document.source_url,
            status="NO_CHANGE",
            relevant=is_relevant,
            products=products,
            event_types=event_types,
            message="No page change was detected.",
        )

    # ------------------------------------------------------
    # PAGE CHANGED
    # ------------------------------------------------------

    change_summary = create_change_summary(
        old_text=old_text,
        new_text=document_text,
    )

    snapshot_path = save_snapshot_file(
        source_id=raw_document.source_id,
        content=document_text,
    )

    change_report_path = save_change_report(
        source_id=raw_document.source_id,
        source_name=raw_document.source_name,
        source_url=raw_document.source_url,
        old_text=old_text,
        new_text=document_text,
        change_summary=change_summary,
        products=products,
        event_types=event_types,
    )

    insert_change(
        source_id=raw_document.source_id,
        source_name=raw_document.source_name,
        source_url=raw_document.source_url,
        change_type="PAGE_CHANGED",
        old_hash=old_hash,
        new_hash=raw_document.content_hash or "",
        old_text=old_text,
        new_text=document_text,
        change_summary=change_summary,
        detected_products=products_text,
        detected_event_types=events_text,
    )

    update_snapshot(
        source_id=raw_document.source_id,
        source_name=raw_document.source_name,
        source_url=raw_document.source_url,
        source_type=source_type,
        page_title=raw_document.title or "Untitled",
        content_hash=raw_document.content_hash or "",
        extracted_text=document_text,
        detected_products=products_text,
        detected_event_types=events_text,
        is_relevant=is_relevant,
        changed=True,
    )

    return CollectionResult(
        source_id=raw_document.source_id,
        source_name=raw_document.source_name,
        source_url=raw_document.source_url,
        status="CHANGED",
        relevant=is_relevant,
        products=products,
        event_types=event_types,
        message=(
            "Page change detected. "
            f"Snapshot saved to: {snapshot_path}. "
            f"Change report saved to: {change_report_path}"
        ),
    )

# ==========================================================
# RUN COLLECTION
# ==========================================================

def run_hintco_collection() -> list[CollectionResult]:
    """
    Run the complete Hintco collection process.
    """

    results: list[CollectionResult] = []

    for source in HINTCO_SOURCES:

        print(f"\nChecking {source['source_name']}...")

        try:

            result = process_source(
                source
            )

        except PlaywrightTimeoutError as exc:

            result = CollectionResult(
                source_id=source["source_id"],
                source_name=source["source_name"],
                source_url=source["url"],
                status="BROWSER_TIMEOUT",
                relevant=False,
                products=[],
                event_types=[],
                message=(
                    "The browser opened the page, "
                    "but it did not finish loading."
                ),
                error=str(exc),
            )

        except requests.HTTPError as exc:

            result = CollectionResult(
                source_id=source["source_id"],
                source_name=source["source_name"],
                source_url=source["url"],
                status="HTTP_ERROR",
                relevant=False,
                products=[],
                event_types=[],
                message=(
                    "The source returned an HTTP error."
                ),
                error=str(exc),
            )

        except requests.Timeout as exc:

            result = CollectionResult(
                source_id=source["source_id"],
                source_name=source["source_name"],
                source_url=source["url"],
                status="TIMEOUT_ERROR",
                relevant=False,
                products=[],
                event_types=[],
                message=(
                    "The request timed out."
                ),
                error=str(exc),
            )

        except requests.RequestException as exc:

            result = CollectionResult(
                source_id=source["source_id"],
                source_name=source["source_name"],
                source_url=source["url"],
                status="REQUEST_ERROR",
                relevant=False,
                products=[],
                event_types=[],
                message=(
                    "The request failed."
                ),
                error=str(exc),
            )

        except Exception as exc:

            result = CollectionResult(
                source_id=source["source_id"],
                source_name=source["source_name"],
                source_url=source["url"],
                status="PROCESSING_ERROR",
                relevant=False,
                products=[],
                event_types=[],
                message=(
                    "Unexpected processing error."
                ),
                error=str(exc),
            )

        results.append(result)

    return results
