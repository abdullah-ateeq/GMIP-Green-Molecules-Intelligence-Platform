from __future__ import annotations

from datetime import datetime, timezone
from time import struct_time

import feedparser

from gmip.collectors.base import GmipCollector
from gmip.models.raw_document import RawDocument


class H2ViewCollector(GmipCollector):
    """
    Collects H2 View articles via its public RSS feed.

    Deliberately RSS-only: does not fetch individual article pages, so it
    never copies full article content, only what the feed itself provides
    (title, link, summary, publication date).
    """

    collector_id = "h2_view"
    collector_name = "H2 View"

    def collect(self) -> list[RawDocument]:
        feed_url = self.source_definition.feed_url

        if not feed_url:
            self.logger.warning(
                "H2ViewCollector has no feed_url configured."
            )
            return []

        parsed_feed = feedparser.parse(feed_url)

        if parsed_feed.bozo and not parsed_feed.entries:
            self.logger.warning(
                "H2 View feed could not be parsed: %s",
                getattr(parsed_feed, "bozo_exception", "unknown error"),
            )
            return []

        raw_documents: list[RawDocument] = []

        for entry in parsed_feed.entries:
            title = entry.get("title")
            link = entry.get("link")

            if not title or not link:
                continue

            raw_documents.append(
                RawDocument(
                    source_id="h2_view",
                    source_name="H2 View",
                    source_url=link,
                    title=title,
                    text=self._clean_summary(entry.get("summary")),
                    status="SUCCESS",
                    content_type="application/rss+xml",
                    published_at=self._parse_published(
                        entry.get("published_parsed")
                    ),
                    collector_id=self.collector_id,
                    collector_name=self.collector_name,
                    metadata={
                        "categories": [
                            tag.get("term")
                            for tag in entry.get("tags", [])
                            if tag.get("term")
                        ],
                    },
                )
            )

        return raw_documents

    @staticmethod
    def _clean_summary(summary: str | None) -> str | None:
        if not summary:
            return None

        # RSS summaries are frequently raw HTML; strip tags crudely here so
        # the parser layer works with plain text. Full HTML cleaning already
        # exists on BaseParser.clean_text() and is applied there too.
        import re

        without_tags = re.sub(r"<[^>]+>", " ", summary)
        collapsed = re.sub(r"\s+", " ", without_tags).strip()

        return collapsed or None

    @staticmethod
    def _parse_published(
        published_parsed: struct_time | None,
    ) -> datetime | None:
        if published_parsed is None:
            return None

        return datetime(
            *published_parsed[:6],
            tzinfo=timezone.utc,
        )
