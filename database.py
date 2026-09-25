from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from config import DATABASE_PATH


@contextmanager
def get_connection():
    """
    Open a SQLite connection and automatically commit or roll back.
    """

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def _ensure_columns(
    connection: sqlite3.Connection,
    table: str,
    columns: dict[str, str],
) -> None:
    """
    Additively migrate a table: add any of `columns` that don't already
    exist, leaving existing data untouched. Safe to call on every startup.
    """

    existing = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})")
    }

    for column_name, column_type in columns.items():
        if column_name not in existing:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"
            )


def initialize_database() -> None:
    """
    Create all required database tables and indexes.
    """

    with get_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                source_id TEXT NOT NULL UNIQUE,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_type TEXT,

                page_title TEXT,
                content_hash TEXT NOT NULL,
                extracted_text TEXT,

                detected_products TEXT,
                detected_event_types TEXT,
                is_relevant INTEGER NOT NULL DEFAULT 0,

                first_seen_at TEXT NOT NULL,
                last_checked_at TEXT NOT NULL,
                last_changed_at TEXT,

                current_status TEXT NOT NULL DEFAULT 'ACTIVE'
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tender_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                source_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,

                change_type TEXT NOT NULL,
                old_hash TEXT,
                new_hash TEXT NOT NULL,

                old_text TEXT,
                new_text TEXT,
                change_summary TEXT,

                detected_products TEXT,
                detected_event_types TEXT,

                detected_at TEXT NOT NULL,
                reviewed INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS collection_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                started_at TEXT NOT NULL,
                completed_at TEXT,
                run_status TEXT NOT NULL,

                sources_checked INTEGER NOT NULL DEFAULT 0,
                sources_changed INTEGER NOT NULL DEFAULT 0,
                errors_count INTEGER NOT NULL DEFAULT 0,

                run_message TEXT
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_changes_detected_at
            ON tender_changes(detected_at)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_changes_source_id
            ON tender_changes(source_id)
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                organization TEXT,
                access_mode TEXT NOT NULL,
                source_category TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                license_required INTEGER NOT NULL DEFAULT 0,

                last_attempted_at TEXT,
                last_successful_at TEXT,
                last_status TEXT,
                last_error TEXT,
                failure_count INTEGER NOT NULL DEFAULT 0,
                next_scheduled_run TEXT
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS intelligence_objects (
                intelligence_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_organisation TEXT,
                parser_name TEXT,

                intelligence_type TEXT,
                title TEXT NOT NULL,
                summary TEXT,
                source_url TEXT,
                published_at TEXT,

                products TEXT,
                countries TEXT,
                companies TEXT,
                categories TEXT,

                identity_key TEXT,
                raw_document_id TEXT,

                content_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,

                collected_at TEXT NOT NULL
            )
            """
        )

        # Additive migration for databases created before identity_key /
        # raw_document_id existed (CREATE TABLE IF NOT EXISTS above does
        # not alter an already-existing table).
        _ensure_columns(
            connection,
            "intelligence_objects",
            {
                "identity_key": "TEXT",
                "raw_document_id": "TEXT",
            },
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_intelligence_source_id
            ON intelligence_objects(source_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_intelligence_identity_key
            ON intelligence_objects(identity_key)
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_documents (
                document_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_name TEXT,
                source_url TEXT,

                title TEXT,
                status TEXT,
                content_type TEXT,
                language TEXT,

                published_at TEXT,
                collected_at TEXT NOT NULL,

                collector_id TEXT,
                collector_name TEXT,
                http_status_code INTEGER,

                content_hash TEXT,
                text_excerpt TEXT,
                metadata_json TEXT
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_raw_documents_source_id
            ON raw_documents(source_id)
            """
        )


def get_snapshot(source_id: str):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM source_snapshots
            WHERE source_id = ?
            """,
            (source_id,),
        ).fetchone()


def insert_initial_snapshot(
    source_id: str,
    source_name: str,
    source_url: str,
    source_type: str,
    page_title: str,
    content_hash: str,
    extracted_text: str,
    detected_products: str,
    detected_event_types: str,
    is_relevant: bool,
) -> None:

    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO source_snapshots (
                source_id,
                source_name,
                source_url,
                source_type,
                page_title,
                content_hash,
                extracted_text,
                detected_products,
                detected_event_types,
                is_relevant,
                first_seen_at,
                last_checked_at,
                last_changed_at,
                current_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                source_name,
                source_url,
                source_type,
                page_title,
                content_hash,
                extracted_text,
                detected_products,
                detected_event_types,
                int(is_relevant),
                now,
                now,
                now,
                "ACTIVE",
            ),
        )


def update_snapshot(
    source_id: str,
    source_name: str,
    source_url: str,
    source_type: str,
    page_title: str,
    content_hash: str,
    extracted_text: str,
    detected_products: str,
    detected_event_types: str,
    is_relevant: bool,
    changed: bool,
) -> None:

    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:

        if changed:
            connection.execute(
                """
                UPDATE source_snapshots
                SET source_name = ?,
                    source_url = ?,
                    source_type = ?,
                    page_title = ?,
                    content_hash = ?,
                    extracted_text = ?,
                    detected_products = ?,
                    detected_event_types = ?,
                    is_relevant = ?,
                    last_checked_at = ?,
                    last_changed_at = ?,
                    current_status = ?
                WHERE source_id = ?
                """,
                (
                    source_name,
                    source_url,
                    source_type,
                    page_title,
                    content_hash,
                    extracted_text,
                    detected_products,
                    detected_event_types,
                    int(is_relevant),
                    now,
                    now,
                    "CHANGED",
                    source_id,
                ),
            )

        else:
            connection.execute(
                """
                UPDATE source_snapshots
                SET source_name = ?,
                    source_url = ?,
                    source_type = ?,
                    page_title = ?,
                    detected_products = ?,
                    detected_event_types = ?,
                    is_relevant = ?,
                    last_checked_at = ?,
                    current_status = ?
                WHERE source_id = ?
                """,
                (
                    source_name,
                    source_url,
                    source_type,
                    page_title,
                    detected_products,
                    detected_event_types,
                    int(is_relevant),
                    now,
                    "NO_CHANGE",
                    source_id,
                ),
            )


def insert_change(
    source_id: str,
    source_name: str,
    source_url: str,
    change_type: str,
    old_hash: str | None,
    new_hash: str,
    old_text: str,
    new_text: str,
    change_summary: str,
    detected_products: str,
    detected_event_types: str,
) -> None:

    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tender_changes (
                source_id,
                source_name,
                source_url,
                change_type,
                old_hash,
                new_hash,
                old_text,
                new_text,
                change_summary,
                detected_products,
                detected_event_types,
                detected_at,
                reviewed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                source_id,
                source_name,
                source_url,
                change_type,
                old_hash,
                new_hash,
                old_text,
                new_text,
                change_summary,
                detected_products,
                detected_event_types,
                now,
            ),
        )


def start_collection_run() -> int:
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO collection_runs (
                started_at,
                run_status
            )
            VALUES (?, ?)
            """,
            (
                now,
                "RUNNING",
            ),
        )

        return int(cursor.lastrowid)


def complete_collection_run(
    run_id: int,
    sources_checked: int,
    sources_changed: int,
    errors_count: int,
    run_message: str,
) -> None:

    now = datetime.now().isoformat(timespec="seconds")

    run_status = "COMPLETED"

    if errors_count > 0:
        run_status = "COMPLETED_WITH_ERRORS"

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE collection_runs
            SET completed_at = ?,
                run_status = ?,
                sources_checked = ?,
                sources_changed = ?,
                errors_count = ?,
                run_message = ?
            WHERE id = ?
            """,
            (
                now,
                run_status,
                sources_checked,
                sources_changed,
                errors_count,
                run_message,
                run_id,
            ),
        )
        # ==========================================================
# DESKTOP DASHBOARD QUERIES
# ==========================================================

def get_dashboard_summary() -> dict:
    """
    Return the main KPI values required by the desktop dashboard.

    Note:
    For the current MVP, an 'opportunity' means a monitored
    source currently classified as relevant.
    """

    with get_connection() as connection:

        opportunities = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM source_snapshots
            WHERE is_relevant = 1
            """
        ).fetchone()["total"]

        latest_changes = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM tender_changes
            WHERE reviewed = 0
            """
        ).fetchone()["total"]

        monitored_sources = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM source_snapshots
            """
        ).fetchone()["total"]

        latest_run = connection.execute(
            """
            SELECT
                completed_at,
                run_status,
                sources_checked,
                sources_changed,
                errors_count
            FROM collection_runs
            WHERE completed_at IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT 1
            """
        ).fetchone()

        # Fallback in case collection_runs is still empty.
        if latest_run is None:

            latest_source_check = connection.execute(
                """
                SELECT MAX(last_checked_at) AS last_checked_at
                FROM source_snapshots
                """
            ).fetchone()

            last_scan = (
                latest_source_check["last_checked_at"]
                if latest_source_check
                else None
            )

            run_status = "NO_RUN_DATA"
            sources_checked = monitored_sources
            sources_changed = 0
            errors_count = 0

        else:

            last_scan = latest_run["completed_at"]
            run_status = latest_run["run_status"]
            sources_checked = latest_run["sources_checked"]
            sources_changed = latest_run["sources_changed"]
            errors_count = latest_run["errors_count"]

        return {
            "opportunities": opportunities,
            "latest_changes": latest_changes,
            "monitored_sources": monitored_sources,
            "last_scan": last_scan,
            "run_status": run_status,
            "sources_checked": sources_checked,
            "sources_changed": sources_changed,
            "errors_count": errors_count,
        }


def get_recent_opportunities(
    limit: int = 10,
) -> list[dict]:
    """
    Return relevant monitored sources for the dashboard
    opportunity table.
    """

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                source_id,
                source_name,
                source_url,
                source_type,
                page_title,
                detected_products,
                detected_event_types,
                last_checked_at,
                last_changed_at,
                current_status
            FROM source_snapshots
            WHERE is_relevant = 1
            ORDER BY
                COALESCE(
                    last_changed_at,
                    last_checked_at
                ) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def get_latest_changes(
    limit: int = 10,
) -> list[dict]:
    """
    Return the newest detected page changes.
    """

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                id,
                source_id,
                source_name,
                source_url,
                change_type,
                change_summary,
                detected_products,
                detected_event_types,
                detected_at,
                reviewed
            FROM tender_changes
            ORDER BY detected_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def get_source_monitor_data() -> list[dict]:
    """
    Return all monitored sources and their current status.
    """

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                source_id,
                source_name,
                source_url,
                source_type,
                detected_products,
                detected_event_types,
                is_relevant,
                first_seen_at,
                last_checked_at,
                last_changed_at,
                current_status
            FROM source_snapshots
            ORDER BY source_name
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ==========================================================
# SOURCE HEALTH / ACCESS-MODE REGISTRY
# ==========================================================
#
# This section is separate from source_snapshots above, which the legacy
# Hintco/Hydrogen Council dashboards already depend on. It tracks the new
# SourceDefinition registry (access mode, licence status, collection
# health) for every configured GMIP source, including sources that are not
# yet enabled.


def sync_source_registry(registry) -> None:
    """
    Upsert every SourceDefinition in the registry into the sources table.

    Only descriptive fields are written here; last_attempted_at,
    last_successful_at, last_status, last_error and failure_count are left
    untouched on existing rows so collection history is not lost on resync.
    """

    with get_connection() as connection:
        for source in registry:
            connection.execute(
                """
                INSERT INTO sources (
                    source_id,
                    source_name,
                    organization,
                    access_mode,
                    source_category,
                    enabled,
                    license_required
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    source_name = excluded.source_name,
                    organization = excluded.organization,
                    access_mode = excluded.access_mode,
                    source_category = excluded.source_category,
                    enabled = excluded.enabled,
                    license_required = excluded.license_required
                """,
                (
                    source.source_id,
                    source.source_name,
                    source.organization,
                    source.access_mode.value,
                    source.source_category.value,
                    int(source.enabled),
                    int(source.license_required),
                ),
            )


def record_source_attempt(
    source_id: str,
    status: str,
    error: str | None = None,
) -> None:
    """
    Record the outcome of one collection attempt for a source.

    status is a free-form label such as SUCCESS, TRANSIENT_FAILURE,
    PERMANENT_FAILURE, PENDING_LICENSE or MISSING_CREDENTIALS.
    """

    now = datetime.now().isoformat(timespec="seconds")
    is_success = status == "SUCCESS"

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE sources
            SET last_attempted_at = ?,
                last_status = ?,
                last_error = ?,
                last_successful_at = CASE
                    WHEN ? THEN ?
                    ELSE last_successful_at
                END,
                failure_count = CASE
                    WHEN ? THEN 0
                    ELSE failure_count + 1
                END
            WHERE source_id = ?
            """,
            (
                now,
                status,
                error,
                is_success,
                now,
                is_success,
                source_id,
            ),
        )


def get_source_registry_status() -> list[dict]:
    """
    Return every registered source with its access mode and health status,
    for the Source Monitor UI.
    """

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                source_id,
                source_name,
                organization,
                access_mode,
                source_category,
                enabled,
                license_required,
                last_attempted_at,
                last_successful_at,
                last_status,
                last_error,
                failure_count
            FROM sources
            ORDER BY source_name
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ==========================================================
# INTELLIGENCE OBJECTS
# ==========================================================
#
# Minimal persistence for gmip.intelligence.IntelligenceObject records
# produced by the new structured parsers (H2 View, Hintco, Hydrogen
# Council). Deliberately not the full future "intelligence database"
# (entities/events/relationships/knowledge-graph tables) — this is scoped
# to storing and listing parsed objects so this phase's parsers have
# somewhere real to persist their output.


def save_intelligence_object(intelligence_object) -> bool:
    """
    Persist one IntelligenceObject.

    Returns True if a new row was inserted, False if a row with the same
    content_hash already existed (i.e. nothing about this piece of
    intelligence has actually changed since it was last seen).
    """

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO intelligence_objects (
                intelligence_id,
                source_id,
                source_organisation,
                parser_name,
                intelligence_type,
                title,
                summary,
                source_url,
                published_at,
                products,
                countries,
                companies,
                categories,
                identity_key,
                raw_document_id,
                content_hash,
                payload_json,
                collected_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                intelligence_object.intelligence_id,
                intelligence_object.source_id,
                intelligence_object.source_organisation,
                intelligence_object.parser_name,
                intelligence_object.intelligence_type.value,
                intelligence_object.title,
                intelligence_object.summary,
                intelligence_object.source_url,
                (
                    intelligence_object.published_at.isoformat()
                    if intelligence_object.published_at
                    else None
                ),
                json.dumps(intelligence_object.products),
                json.dumps(intelligence_object.countries),
                json.dumps(intelligence_object.companies),
                json.dumps(intelligence_object.categories),
                intelligence_object.identity_key,
                intelligence_object.raw_document_id,
                intelligence_object.content_hash,
                intelligence_object.to_json(indent=None),
                intelligence_object.collected_at.isoformat(),
            ),
        )

        return cursor.rowcount > 0


def classify_and_save_intelligence_object(intelligence_object) -> dict:
    """
    Persist one IntelligenceObject with item-level change detection.

    Looks up the most recent previously-stored object sharing the same
    identity_key (the same logical tender lot / report / item, independent
    of whether its content has changed) and classifies this collection as:

      - "NEW"       — no previous object with this identity_key exists
      - "UPDATED"   — a previous object exists with a different content_hash
      - "UNCHANGED" — a previous object exists with the same content_hash

    This is the structured equivalent of the legacy "page changed" check,
    but at the level of one logical item rather than one whole webpage.
    Returns a dict with the classification, a lightweight field-level diff
    against the previous version (when UPDATED), and whether a new row was
    actually inserted.
    """

    with get_connection() as connection:
        previous_row = connection.execute(
            """
            SELECT *
            FROM intelligence_objects
            WHERE identity_key = ?
            ORDER BY collected_at DESC
            LIMIT 1
            """,
            (intelligence_object.identity_key,),
        ).fetchone()

    previous = dict(previous_row) if previous_row else None

    if previous is None:
        change_type = "NEW"
    elif previous["content_hash"] == intelligence_object.content_hash:
        change_type = "UNCHANGED"
    else:
        change_type = "UPDATED"

    diff: dict[str, dict] = {}

    if change_type == "UPDATED" and previous is not None:
        try:
            previous_payload = json.loads(previous.get("payload_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            previous_payload = {}

        comparable_fields = (
            "title",
            "summary",
            "fid_date",
            "cod_date",
            "tender_type",
            "project_stage",
        )

        for field_name in comparable_fields:
            old_value = previous_payload.get(field_name)
            new_value = getattr(intelligence_object, field_name, None)

            if hasattr(new_value, "isoformat"):
                new_value = new_value.isoformat()

            if old_value != new_value:
                diff[field_name] = {"old": old_value, "new": new_value}

        old_tender_status = (previous_payload.get("tender") or {}).get(
            "tender_status"
        )
        new_tender_status = (
            intelligence_object.tender.tender_status
            if intelligence_object.tender
            else None
        )

        if old_tender_status != new_tender_status:
            diff["tender_status"] = {
                "old": old_tender_status,
                "new": new_tender_status,
            }

    inserted = save_intelligence_object(intelligence_object)

    return {
        "change_type": change_type,
        "diff": diff,
        "inserted": inserted,
        "previous_intelligence_id": (
            previous["intelligence_id"] if previous else None
        ),
    }


def save_raw_document(raw_document) -> None:
    """
    Persist one RawDocument as an audit-trail row.

    Unlike intelligence_objects, this is not deduplicated — every
    collection attempt is logged, successful or not, so source health and
    provenance can be reconstructed later. Full HTML is not stored here
    (already saved to Data/Raw/ by the legacy collector); only a bounded
    text excerpt is kept for quick inspection.
    """

    text_excerpt = (raw_document.text or "")[:2000] or None

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO raw_documents (
                document_id,
                source_id,
                source_name,
                source_url,
                title,
                status,
                content_type,
                language,
                published_at,
                collected_at,
                collector_id,
                collector_name,
                http_status_code,
                content_hash,
                text_excerpt,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw_document.document_id,
                raw_document.source_id,
                raw_document.source_name,
                raw_document.source_url,
                raw_document.title,
                raw_document.status,
                raw_document.content_type,
                raw_document.language,
                (
                    raw_document.published_at.isoformat()
                    if raw_document.published_at
                    else None
                ),
                raw_document.collected_at.isoformat(),
                raw_document.collector_id,
                raw_document.collector_name,
                raw_document.http_status_code,
                raw_document.content_hash,
                text_excerpt,
                json.dumps(raw_document.metadata or {}),
            ),
        )


def get_recent_raw_documents(
    limit: int = 20,
    source_id: str | None = None,
) -> list[dict]:
    """Return the most recently collected raw documents."""

    with get_connection() as connection:
        if source_id:
            rows = connection.execute(
                """
                SELECT *
                FROM raw_documents
                WHERE source_id = ?
                ORDER BY collected_at DESC
                LIMIT ?
                """,
                (source_id, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM raw_documents
                ORDER BY collected_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]


def get_recent_intelligence_objects(
    limit: int = 20,
    source_id: str | None = None,
) -> list[dict]:
    """Return the most recently collected intelligence objects."""

    with get_connection() as connection:
        if source_id:
            rows = connection.execute(
                """
                SELECT
                    intelligence_id,
                    source_id,
                    source_organisation,
                    parser_name,
                    intelligence_type,
                    title,
                    summary,
                    source_url,
                    published_at,
                    products,
                    countries,
                    companies,
                    categories,
                    payload_json,
                    collected_at
                FROM intelligence_objects
                WHERE source_id = ?
                ORDER BY collected_at DESC
                LIMIT ?
                """,
                (source_id, limit),
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT
                    intelligence_id,
                    source_id,
                    source_organisation,
                    parser_name,
                    intelligence_type,
                    title,
                    summary,
                    source_url,
                    published_at,
                    products,
                    countries,
                    companies,
                    categories,
                    payload_json,
                    collected_at
                FROM intelligence_objects
                ORDER BY collected_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ==========================================================
# INTELLIGENCE ANALYTICS
# ==========================================================
#
# Lightweight, honest aggregations over intelligence_objects for the
# executive dashboard. These compute real counts from collected data —
# nothing here is a placeholder or fabricated figure. Widgets with no
# underlying data model yet (opportunity scoring, market signals) are
# deliberately not implemented here; see the web dashboard's empty states.


def get_country_mentions(limit: int = 15) -> list[dict]:
    """Count how many intelligence objects mention each country."""

    counts: dict[str, int] = {}

    with get_connection() as connection:
        rows = connection.execute(
            "SELECT countries FROM intelligence_objects"
        ).fetchall()

    for row in rows:
        try:
            countries = json.loads(row["countries"] or "[]")
        except (json.JSONDecodeError, TypeError):
            continue

        for country in countries:
            counts[country] = counts.get(country, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)

    return [
        {"country": country, "mentions": mentions}
        for country, mentions in ranked[:limit]
    ]


def get_source_type_distribution() -> list[dict]:
    """Count intelligence objects grouped by their source organisation."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                source_organisation,
                COUNT(*) AS total
            FROM intelligence_objects
            GROUP BY source_organisation
            ORDER BY total DESC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def get_intelligence_type_distribution() -> list[dict]:
    """Count intelligence objects grouped by intelligence_type."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                intelligence_type,
                COUNT(*) AS total
            FROM intelligence_objects
            GROUP BY intelligence_type
            ORDER BY total DESC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def get_activity_timeseries(days: int = 30) -> list[dict]:
    """
    Daily count of collected intelligence objects over the trailing window,
    for the dashboard's activity chart.
    """

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                substr(collected_at, 1, 10) AS day,
                COUNT(*) AS total
            FROM intelligence_objects
            WHERE collected_at >= datetime('now', ?)
            GROUP BY day
            ORDER BY day ASC
            """,
            (f"-{days} days",),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def get_intelligence_count(since_days: int | None = None) -> int:
    """Total intelligence objects collected, optionally within a window."""

    with get_connection() as connection:
        if since_days is not None:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM intelligence_objects
                WHERE collected_at >= datetime('now', ?)
                """,
                (f"-{since_days} days",),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM intelligence_objects"
            ).fetchone()

        return row["total"]


def get_tender_counts() -> dict:
    """Open vs. closed tender counts, from real Hintco tender intelligence."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT payload_json
            FROM intelligence_objects
            WHERE intelligence_type = 'tender'
            """
        ).fetchall()

    open_count = 0
    closed_count = 0

    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
        except (json.JSONDecodeError, TypeError):
            continue

        status = (payload.get("tender") or {}).get("tender_status")

        if status == "Open":
            open_count += 1
        elif status == "Closed":
            closed_count += 1

    return {"open": open_count, "closed": closed_count, "total": len(rows)}