from __future__ import annotations

import pytest

from gmip.config.access_mode import SourceAccessMode, SourceCategory
from gmip.config.source_definition import SourceDefinition
from gmip.config.sources_registry import SOURCE_REGISTRY, get_source_definition


def test_source_definition_builds_with_required_fields() -> None:
    source = SourceDefinition(
        source_id="example",
        source_name="Example Source",
        organization="Example Org",
        source_category=SourceCategory.INDUSTRY_MEDIA,
        access_mode=SourceAccessMode.PUBLIC_RSS,
        feed_url="https://example.com/feed/",
    )

    assert source.source_id == "example"
    assert source.feed_url == "https://example.com/feed/"
    assert source.is_active is True


def test_source_definition_rejects_empty_source_id() -> None:
    with pytest.raises(ValueError):
        SourceDefinition(
            source_id="   ",
            source_name="Example Source",
            organization="Example Org",
            source_category=SourceCategory.INDUSTRY_MEDIA,
            access_mode=SourceAccessMode.PUBLIC_RSS,
        )


def test_source_definition_rejects_bad_url_scheme() -> None:
    with pytest.raises(ValueError):
        SourceDefinition(
            source_id="example",
            source_name="Example Source",
            organization="Example Org",
            source_category=SourceCategory.INDUSTRY_MEDIA,
            access_mode=SourceAccessMode.PUBLIC_RSS,
            feed_url="ftp://example.com/feed/",
        )


def test_disabled_pending_license_is_not_active() -> None:
    source = SourceDefinition(
        source_id="example",
        source_name="Example Source",
        organization="Example Org",
        source_category=SourceCategory.INDUSTRY_MEDIA,
        access_mode=SourceAccessMode.DISABLED_PENDING_LICENSE,
        enabled=False,
    )

    assert source.is_active is False


def test_source_registry_has_seven_sources_with_unique_ids() -> None:
    assert len(SOURCE_REGISTRY) == 7

    source_ids = [source.source_id for source in SOURCE_REGISTRY]
    assert len(source_ids) == len(set(source_ids))


def test_source_registry_h2_view_is_enabled_public_rss() -> None:
    h2_view = get_source_definition("h2_view")

    assert h2_view is not None
    assert h2_view.access_mode == SourceAccessMode.PUBLIC_RSS
    assert h2_view.enabled is True
    assert h2_view.feed_url


def test_source_registry_restricted_sources_are_disabled() -> None:
    for source_id in (
        "hydrogen_insight",
        "recharge_news",
        "sp_global_commodity_insights",
        "argus_media",
    ):
        source = get_source_definition(source_id)

        assert source is not None
        assert source.enabled is False
        assert source.is_active is False


def test_get_source_definition_returns_none_for_unknown_id() -> None:
    assert get_source_definition("does_not_exist") is None
