import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

from config import DATABASE_PATH


st.set_page_config(
    page_title="Hintco Green Molecules Monitor",
    page_icon="🌍",
    layout="wide",
)


def load_data(
    query: str,
) -> pd.DataFrame:
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        return pd.read_sql_query(
            query,
            connection,
        )

    finally:
        connection.close()


st.title(
    "Hintco Green Hydrogen, Ammonia "
    "and Methanol Supply Tender Monitor"
)

st.caption(
    "Monitoring Hintco purchase auctions, tender updates, "
    "deadline changes, amendments and awards."
)


source_status = load_data(
    """
    SELECT
        source_name AS Source,
        source_type AS "Source Type",
        source_url AS "Official URL",
        detected_products AS Products,
        detected_event_types AS "Possible Events",
        CASE
            WHEN is_relevant = 1 THEN 'Yes'
            ELSE 'No'
        END AS Relevant,
        current_status AS Status,
        last_checked_at AS "Last Checked",
        last_changed_at AS "Last Changed"
    FROM source_snapshots
    ORDER BY source_name
    """
)


changes = load_data(
    """
    SELECT
        source_name AS Source,
        source_url AS "Official URL",
        detected_products AS Products,
        detected_event_types AS "Possible Events",
        detected_at AS "Detected At",
        change_summary AS "Change Summary",
        CASE
            WHEN reviewed = 1 THEN 'Yes'
            ELSE 'No'
        END AS Reviewed
    FROM tender_changes
    ORDER BY detected_at DESC
    """
)


runs = load_data(
    """
    SELECT
        started_at AS "Started At",
        completed_at AS "Completed At",
        run_status AS Status,
        sources_checked AS "Sources Checked",
        sources_changed AS "Sources Changed",
        errors_count AS Errors
    FROM collection_runs
    ORDER BY id DESC
    LIMIT 20
    """
)


total_sources = len(source_status)

relevant_sources = (
    int(
        source_status["Relevant"]
        .eq("Yes")
        .sum()
    )
    if not source_status.empty
    else 0
)

total_changes = len(changes)

current_changed_sources = (
    int(
        source_status["Status"]
        .eq("CHANGED")
        .sum()
    )
    if not source_status.empty
    else 0
)


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Sources Monitored",
    total_sources,
)

col2.metric(
    "Relevant Sources",
    relevant_sources,
)

col3.metric(
    "Total Changes Detected",
    total_changes,
)

col4.metric(
    "Sources Changed Latest Run",
    current_changed_sources,
)


st.divider()


product_filter = st.multiselect(
    "Filter by product",
    options=[
        "RFNBO Hydrogen",
        "RFNBO Ammonia",
        "RFNBO Methanol",
    ],
)


filtered_sources = source_status.copy()
filtered_changes = changes.copy()

if product_filter:
    product_pattern = "|".join(product_filter)

    if not filtered_sources.empty:
        filtered_sources = filtered_sources[
            filtered_sources["Products"]
            .fillna("")
            .str.contains(
                product_pattern,
                case=False,
                regex=True,
            )
        ]

    if not filtered_changes.empty:
        filtered_changes = filtered_changes[
            filtered_changes["Products"]
            .fillna("")
            .str.contains(
                product_pattern,
                case=False,
                regex=True,
            )
        ]


tab1, tab2, tab3 = st.tabs(
    [
        "Source Status",
        "Detected Changes",
        "Collection History",
    ]
)


with tab1:
    st.subheader("Hintco Sources")

    if filtered_sources.empty:
        st.info(
            "No source records are available. "
            "Run python app.py first."
        )

    else:
        st.dataframe(
            filtered_sources,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Official URL": st.column_config.LinkColumn(
                    "Official URL"
                ),
            },
        )


with tab2:
    st.subheader("Latest Tender Page Changes")

    if filtered_changes.empty:
        st.success(
            "No page changes have been detected "
            "since monitoring began."
        )

    else:
        st.dataframe(
            filtered_changes,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Official URL": st.column_config.LinkColumn(
                    "Official URL"
                ),
                "Change Summary": st.column_config.TextColumn(
                    "Change Summary",
                    width="large",
                ),
            },
        )


with tab3:
    st.subheader("Collection Run History")

    if runs.empty:
        st.info(
            "No collection runs have been recorded."
        )

    else:
        st.dataframe(
            runs,
            use_container_width=True,
            hide_index=True,
        )


st.divider()

st.caption(
    f"Dashboard refreshed: "
    f"{datetime.now().strftime('%d %b %Y %H:%M:%S')}"
)