"""
End-to-end GMIP intelligence pipeline runner (Steps 4-6 acceptance test).

Demonstrates, for both Hintco and Hydrogen Council:

    Collector -> RawDocument -> ParserRegistry -> IntelligenceObject
        -> Database (raw_documents + intelligence_objects)

Reuses the existing collector_manager.CollectorManager (which already runs
both collectors) and hintco_collector.process_source() (which already
invokes the structured-parsing hook additively). This script adds nothing
new to the collection path itself — it runs it, then reports what actually
landed in the database, per source.
"""
from __future__ import annotations

from collectors.collector_manager import CollectorManager
from database import (
    get_recent_intelligence_objects,
    get_recent_raw_documents,
    initialize_database,
)


def main() -> int:
    initialize_database()

    print("=" * 70)
    print("GMIP END-TO-END INTELLIGENCE PIPELINE RUN")
    print("=" * 70)

    manager = CollectorManager()

    print(f"\nRegistered collectors: {[c.collector_id for c in manager.collectors]}")

    results = manager.run_all_collectors()

    print(f"\nCollection complete. {len(results)} source(s) processed.")

    errors = [r for r in results if getattr(r, "error", None)]
    print(f"  Errors: {len(errors)}")
    for error_result in errors:
        print(f"    - {error_result.source_id}: {error_result.message}")

    for source_id, source_organisation in (
        ("hintco", "Hintco"),
        ("hydrogen_council", "Hydrogen Council"),
    ):
        print("\n" + "-" * 70)
        print(f"{source_organisation.upper()} — INTELLIGENCE OBJECTS")
        print("-" * 70)

        raw_docs = get_recent_raw_documents(limit=100, source_id=None)
        raw_docs = [
            d for d in raw_docs if d["source_id"].startswith(
                "hintco" if source_id == "hintco" else "hydrogen_council"
            )
        ]
        print(f"RawDocuments collected this session: {len(raw_docs)}")

        objects = get_recent_intelligence_objects(
            limit=10, source_id=source_id
        )

        if not objects:
            print("No structured intelligence objects yet for this source.")
            continue

        # Prefer a genuine structured card over the generic whole-page
        # fallback (company_update/other), to actually showcase extraction.
        example = next(
            (o for o in objects if o["intelligence_type"] not in (
                "company_update", "other",
            )),
            objects[0],
        )
        print(f"\nExample object ({len(objects)} total shown, most recent first):")
        print(f"  Title:             {example['title']}")
        print(f"  Source:            {example['source_organisation']}")
        print(f"  Intelligence Type: {example['intelligence_type']}")
        print(f"  Published:         {example['published_at']}")
        print(f"  Products:          {example['products']}")
        print(f"  Countries:         {example['countries']}")
        print(f"  Companies:         {example['companies']}")
        print(f"  Summary:           {(example['summary'] or '')[:150]}")
        print(f"  Source URL:        {example['source_url']}")

    print("\n" + "=" * 70)
    print("RUN COMPLETE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
