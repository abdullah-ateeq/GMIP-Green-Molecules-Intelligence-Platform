"""
FastAPI layer for the GMIP web frontend.

Wraps the existing database.py read functions as JSON endpoints. This file
contains no business logic of its own — it is a thin, read-only API over
the same SQLite database the legacy app, Streamlit dashboard, and desktop
UI already use. Nothing here duplicates or replaces those.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import database
from collectors.collector_manager import CollectorManager
from gmip.config import SOURCE_REGISTRY

app = FastAPI(
    title="GMIP API",
    description="Read-only API over the GMIP intelligence database.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _serialize_intelligence_row(row: dict) -> dict:
    payload_json = row.pop("payload_json", None)
    payload: dict = {}

    if payload_json:
        try:
            payload = json.loads(payload_json)
        except (json.JSONDecodeError, TypeError):
            payload = {}

    source_available = row.get("source_available")

    return {
        **row,
        "products": _parse_json_list(row.get("products")),
        "countries": _parse_json_list(row.get("countries")),
        "companies": _parse_json_list(row.get("companies")),
        "categories": _parse_json_list(row.get("categories")),
        "confidence": payload.get("confidence"),
        "importance": payload.get("importance"),
        "why_it_matters": payload.get("why_it_matters"),
        "tender_status": (payload.get("tender") or {}).get("tender_status"),
        "tender_region": (payload.get("tender") or {}).get("region"),
        "offtake_product": (payload.get("offtake") or {}).get("product"),
        "offtake_volume": (payload.get("offtake") or {}).get("volume"),
        "offtake_duration": (payload.get("offtake") or {}).get("duration"),
        # None = never checked (the honest default — see gmip/provenance.py).
        "source_available": (
            None if source_available is None else bool(source_available)
        ),
    }


@app.on_event("startup")
def on_startup() -> None:
    database.initialize_database()
    database.sync_source_registry(SOURCE_REGISTRY)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/dashboard/summary")
def dashboard_summary() -> dict:
    return database.get_dashboard_summary()


@app.get("/api/intelligence/recent")
def intelligence_recent(limit: int = 20, source_id: str | None = None) -> list[dict]:
    rows = database.get_recent_intelligence_objects(
        limit=limit, source_id=source_id
    )
    return [_serialize_intelligence_row(row) for row in rows]


@app.get("/api/opportunities/recent")
def opportunities_recent(limit: int = 10) -> list[dict]:
    return database.get_recent_opportunities(limit=limit)


@app.get("/api/business/kpis")
def business_kpis() -> dict:
    return database.get_business_kpis()


@app.get("/api/business/activity")
def business_activity(days: int = 30) -> list[dict]:
    return database.get_business_activity_series(days=days)


@app.get("/api/business/source-categories")
def business_source_categories() -> list[dict]:
    return database.get_source_category_distribution()


@app.get("/api/business/opportunities")
def business_opportunities(limit: int = 20) -> list[dict]:
    return database.get_opportunity_radar(limit=limit)


@app.get("/api/business/signals")
def business_signals() -> list[dict]:
    return database.get_market_signals()


@app.get("/api/changes/recent")
def changes_recent(limit: int = 10) -> list[dict]:
    return database.get_latest_changes(limit=limit)


@app.get("/api/sources")
def sources() -> list[dict]:
    return database.get_source_registry_status()


def _serialize_entity(row: dict) -> dict:
    return {
        "entity_id": row["entity_id"],
        "entity_type": row["entity_type"],
        "canonical_name": row["canonical_name"],
        "aliases": _parse_json_list(row.get("aliases_json")),
        "country": row.get("country"),
        "description": row.get("description"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _serialize_profile(profile: dict | None) -> dict:
    if profile is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {
        "entity": _serialize_entity(profile["entity"]),
        "mention_count": profile["mention_count"],
        "countries": profile.get("countries", []),
        "products": profile.get("products", []),
        "latest_intelligence": [
            {
                "intelligence_object_id": m["intelligence_object_id"],
                "title": m["title"],
                "source_url": m["source_url"],
                "intelligence_type": m["intelligence_type"],
                "collected_at": m["intelligence_collected_at"],
                "original_mention": m["original_mention"],
            }
            for m in profile["latest_intelligence"]
        ],
        "relationships": profile["relationships"],
    }


@app.get("/api/entities/companies")
def entities_companies(limit: int = 200) -> list[dict]:
    return [
        _serialize_entity(row)
        for row in database.get_entities("COMPANY", limit=limit)
    ]


@app.get("/api/entities/companies/{entity_id}")
def entities_company_detail(entity_id: str) -> dict:
    return _serialize_profile(database.get_company_profile(entity_id))


@app.get("/api/entities/projects")
def entities_projects(limit: int = 200) -> list[dict]:
    # Only projects with at least one real intelligence mention — a
    # seeded-but-never-mentioned project must not appear as if it were a
    # real result (entity-extraction brief, section 29).
    return [
        _serialize_entity(row)
        for row in database.get_entities_with_evidence("PROJECT", limit=limit)
    ]


@app.get("/api/entities/projects/{entity_id}")
def entities_project_detail(entity_id: str) -> dict:
    return _serialize_profile(database.get_project_profile(entity_id))


@app.get("/api/entities/search")
def entities_search(q: str, entity_type: str | None = None) -> list[dict]:
    return [
        _serialize_entity(row)
        for row in database.search_entities(q, entity_type=entity_type)
    ]


@app.get("/api/intelligence/search")
def intelligence_search(q: str, limit: int = 10) -> list[dict]:
    return database.search_intelligence_objects(q, limit=limit)


@app.get("/api/analytics/countries")
def analytics_countries(limit: int = 15) -> list[dict]:
    return database.get_country_mentions(limit=limit)


@app.get("/api/analytics/source-types")
def analytics_source_types() -> list[dict]:
    return database.get_source_type_distribution()


@app.get("/api/analytics/intelligence-types")
def analytics_intelligence_types() -> list[dict]:
    return database.get_intelligence_type_distribution()


@app.get("/api/analytics/activity")
def analytics_activity(days: int = 30) -> list[dict]:
    return database.get_activity_timeseries(days=days)


@app.get("/api/analytics/intelligence-count")
def analytics_intelligence_count(since_days: int | None = None) -> dict:
    return {
        "total": database.get_intelligence_count(since_days=since_days),
    }


@app.get("/api/analytics/tenders")
def analytics_tenders() -> dict:
    return database.get_tender_counts()


@app.post("/api/collect/run")
def collect_run() -> dict:
    """
    Trigger a real collection run across every registered collector
    (Hintco, Hydrogen Council, H2 View) and report what happened.

    Also records this as a row in collection_runs — the same table
    app.py's CLI path writes to — so the dashboard's "Last Market Scan"
    KPI reflects a web-triggered refresh too, not just CLI runs.

    Synchronous and can take a couple of minutes (Hintco alone launches a
    headless browser per source) — the frontend's Refresh button is
    expected to show a loading state for the duration of this call.
    """
    started_at = time.time()
    run_id = database.start_collection_run()

    manager = CollectorManager()
    results = manager.run_all_collectors()

    duration_seconds = round(time.time() - started_at, 1)
    errors = [r for r in results if getattr(r, "error", None)]
    changed = [r for r in results if getattr(r, "status", None) == "CHANGED"]

    run_message = (
        f"Web refresh: checked {len(results)} source(s), "
        f"detected {len(changed)} change(s), "
        f"recorded {len(errors)} error(s)."
    )

    database.complete_collection_run(
        run_id=run_id,
        sources_checked=len(results),
        sources_changed=len(changed),
        errors_count=len(errors),
        run_message=run_message,
    )

    return {
        "duration_seconds": duration_seconds,
        "sources_checked": len(results),
        "errors_count": len(errors),
        "results": [asdict(result) for result in results],
    }
