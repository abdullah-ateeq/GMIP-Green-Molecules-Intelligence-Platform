import sqlite3
import sys
from pathlib import Path

import pandas as pd

from config import (
    DATABASE_PATH,
    EXCEL_OUTPUT_PATH,
)
from database import (
    complete_collection_run,
    initialize_database,
    start_collection_run,
)
from hintco_collector import run_hintco_collection


def export_database_to_excel() -> None:
    """
    Export the current source status, detected changes and run history
    into a single Excel workbook.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        source_status = pd.read_sql_query(
            """
            SELECT
                source_name AS "Source",
                source_type AS "Source Type",
                source_url AS "Official URL",
                page_title AS "Page Title",
                detected_products AS "Products",
                detected_event_types AS "Possible Events",
                CASE
                    WHEN is_relevant = 1 THEN 'Yes'
                    ELSE 'No'
                END AS "Relevant",
                current_status AS "Current Status",
                first_seen_at AS "First Seen",
                last_checked_at AS "Last Checked",
                last_changed_at AS "Last Changed"
            FROM source_snapshots
            ORDER BY source_name
            """,
            connection,
        )

        changes = pd.read_sql_query(
            """
            SELECT
                source_name AS "Source",
                source_url AS "Official URL",
                change_type AS "Change Type",
                detected_products AS "Products",
                detected_event_types AS "Possible Events",
                detected_at AS "Detected At",
                change_summary AS "Change Summary",
                CASE
                    WHEN reviewed = 1 THEN 'Yes'
                    ELSE 'No'
                END AS "Reviewed"
            FROM tender_changes
            ORDER BY detected_at DESC
            """,
            connection,
        )

        runs = pd.read_sql_query(
            """
            SELECT
                started_at AS "Started At",
                completed_at AS "Completed At",
                run_status AS "Run Status",
                sources_checked AS "Sources Checked",
                sources_changed AS "Sources Changed",
                errors_count AS "Errors",
                run_message AS "Message"
            FROM collection_runs
            ORDER BY id DESC
            """,
            connection,
        )

        with pd.ExcelWriter(
            EXCEL_OUTPUT_PATH,
            engine="openpyxl",
        ) as writer:

            source_status.to_excel(
                writer,
                sheet_name="Source Status",
                index=False,
            )

            changes.to_excel(
                writer,
                sheet_name="Detected Changes",
                index=False,
            )

            runs.to_excel(
                writer,
                sheet_name="Collection Runs",
                index=False,
            )

            format_excel_workbook(writer)

    finally:
        connection.close()


def format_excel_workbook(writer) -> None:
    """
    Apply basic formatting to each Excel worksheet.
    """

    workbook = writer.book

    for worksheet in workbook.worksheets:

        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for column_cells in worksheet.columns:
            maximum_length = 0

            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                if cell.value is not None:
                    maximum_length = max(
                        maximum_length,
                        len(str(cell.value)),
                    )

            worksheet.column_dimensions[
                column_letter
            ].width = min(maximum_length + 2, 60)


def print_result(result) -> None:
    print()
    print("-" * 70)
    print(f"Source: {result.source_name}")
    print(f"Status: {result.status}")
    print(f"Relevant: {result.relevant}")

    products = (
        ", ".join(result.products)
        if result.products
        else "None"
    )

    events = (
        ", ".join(result.event_types)
        if result.event_types
        else "None"
    )

    print(f"Products: {products}")
    print(f"Possible Events: {events}")
    print(f"URL: {result.source_url}")
    print(f"Message: {result.message}")

    if result.error:
        print(f"Error: {result.error}")


def main() -> int:
    initialize_database()

    run_id = start_collection_run()

    print("=" * 70)
    print(
        "HINTCO GREEN HYDROGEN, AMMONIA "
        "AND METHANOL TENDER MONITOR"
    )
    print("=" * 70)

    try:
        results = run_hintco_collection()

        for result in results:
            print_result(result)

        sources_checked = len(results)

        sources_changed = sum(
            1
            for result in results
            if result.status == "CHANGED"
        )

        errors_count = sum(
            1
            for result in results
            if result.error is not None
        )

        export_database_to_excel()

        run_message = (
            f"Checked {sources_checked} source(s), "
            f"detected {sources_changed} change(s), "
            f"and recorded {errors_count} error(s)."
        )

        complete_collection_run(
            run_id=run_id,
            sources_checked=sources_checked,
            sources_changed=sources_changed,
            errors_count=errors_count,
            run_message=run_message,
        )

        # Export again so the completed run is included.
        export_database_to_excel()

        print()
        print("=" * 70)
        print("COLLECTION COMPLETE")
        print("=" * 70)
        print(run_message)
        print(f"Database: {DATABASE_PATH}")
        print(f"Excel report: {EXCEL_OUTPUT_PATH}")

        return 0

    except Exception as exc:
        complete_collection_run(
            run_id=run_id,
            sources_checked=0,
            sources_changed=0,
            errors_count=1,
            run_message=f"Collection failed: {exc}",
        )

        print()
        print("=" * 70)
        print("COLLECTION FAILED")
        print("=" * 70)
        print(str(exc))

        return 1


if __name__ == "__main__":
    sys.exit(main())