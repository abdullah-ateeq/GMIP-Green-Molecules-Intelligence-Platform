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

from fastapi import FastAPI
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
