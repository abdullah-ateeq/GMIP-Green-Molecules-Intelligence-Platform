from __future__ import annotations

from gmip.models.raw_document import RawDocument


def test_raw_document() -> None:
    print("=" * 70)
    print("GMIP RAW DOCUMENT TEST")
    print("=" * 70)

    raw_document = RawDocument(
        source_id="hydrogen_council_intelligence",
        source_name="Hydrogen Council Intelligence",
        source_url=(
            "https://hydrogencouncil.com/en/intelligence/"
        ),
        title="Hydrogen Council Intelligence",
        html="""
            <html>
                <body>
                    <h1>Hydrogen Council Intelligence</h1>
                    <p>Green hydrogen market report.</p>
                </body>
            </html>
        """,
        text=(
            "Hydrogen Council Intelligence "
            "Green hydrogen market report."
        ),
        status="SUCCESS",
        content_type="text/html",
        language="en",
        collector_id="hydrogen_council",
        collector_name="Hydrogen Council",
        http_status_code=200,
        response_time_seconds=1.25,
        metadata={
            "source_category": "intelligence",
            "collection_method": "requests",
        },
    )

    assert raw_document.source_id == (
        "hydrogen_council_intelligence"
    )

    assert raw_document.status == "SUCCESS"
    assert raw_document.has_content is True
    assert raw_document.is_successful is True
    assert raw_document.is_error is False
    assert raw_document.content_hash is not None
    assert len(raw_document.content_hash) == 64

    duplicate_document = RawDocument(
        source_id="hydrogen_council_intelligence",
        source_name="Hydrogen Council Intelligence",
        source_url=(
            "https://hydrogencouncil.com/en/intelligence/"
        ),
        title="Hydrogen Council Intelligence",
        html="""
            <html>
                <body>
                    <h1>Hydrogen Council Intelligence</h1>
                    <p>Green hydrogen market report.</p>
                </body>
            </html>
        """,
        text=(
            "Hydrogen Council Intelligence "
            "Green hydrogen market report."
        ),
        status="SUCCESS",
        content_type="text/html",
        language="en",
    )

    assert (
        raw_document.content_hash
        == duplicate_document.content_hash
    )

    assert (
        raw_document.document_id
        != duplicate_document.document_id
    )

    print(raw_document.to_json())

    print("=" * 70)
    print("TEST PASSED")
    print(f"Document ID: {raw_document.document_id}")
    print(f"Content Hash: {raw_document.content_hash}")
    print(f"Has Content: {raw_document.has_content}")
    print("=" * 70)


if __name__ == "__main__":
    test_raw_document()