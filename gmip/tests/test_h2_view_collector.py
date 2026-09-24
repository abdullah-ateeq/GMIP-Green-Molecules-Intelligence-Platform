from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import patch

from gmip.collectors.h2_view_collector import H2ViewCollector
from gmip.config import get_source_definition


def _fake_parsed_feed(entries: list[dict], bozo: bool = False) -> SimpleNamespace:
    return SimpleNamespace(bozo=bozo, bozo_exception=None, entries=entries)


def test_collect_builds_raw_documents_from_feed_entries() -> None:
    source = get_source_definition("h2_view")
    collector = H2ViewCollector(source)

    fake_entries = [
        {
            "title": "New green hydrogen plant announced",
            "link": "https://www.h2-view.com/story/example/",
            "summary": "<p>A new plant was announced <b>today</b>.</p>",
            "published_parsed": time.struct_time(
                (2026, 9, 20, 10, 0, 0, 0, 0, 0)
            ),
            "tags": [{"term": "Projects"}, {"term": "Green Hydrogen"}],
        }
    ]

    with patch(
        "gmip.collectors.h2_view_collector.feedparser.parse",
        return_value=_fake_parsed_feed(fake_entries),
    ):
        documents = collector.collect()

    assert len(documents) == 1

    document = documents[0]
    assert document.source_id == "h2_view"
    assert document.title == "New green hydrogen plant announced"
    assert document.source_url == "https://www.h2-view.com/story/example/"
    assert document.text == "A new plant was announced today ."
    assert document.published_at is not None
    assert document.published_at.year == 2026
    assert document.metadata["categories"] == ["Projects", "Green Hydrogen"]


def test_collect_skips_entries_missing_title_or_link() -> None:
    source = get_source_definition("h2_view")
    collector = H2ViewCollector(source)

    fake_entries = [
        {"title": "", "link": "https://www.h2-view.com/story/example/"},
        {"title": "No link here"},
    ]

    with patch(
        "gmip.collectors.h2_view_collector.feedparser.parse",
        return_value=_fake_parsed_feed(fake_entries),
    ):
        documents = collector.collect()

    assert documents == []


def test_collect_returns_empty_list_on_unparseable_feed() -> None:
    source = get_source_definition("h2_view")
    collector = H2ViewCollector(source)

    with patch(
        "gmip.collectors.h2_view_collector.feedparser.parse",
        return_value=_fake_parsed_feed([], bozo=True),
    ):
        documents = collector.collect()

    assert documents == []


def test_collect_returns_empty_list_without_feed_url() -> None:
    source = get_source_definition("hydrogen_insight")
    collector = H2ViewCollector(source)

    documents = collector.collect()

    assert documents == []
