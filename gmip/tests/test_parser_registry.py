from __future__ import annotations

from gmip.parsers import (
    H2ViewParser,
    HintcoParser,
    HydrogenCouncilParser,
    build_default_registry,
)
from gmip.parsers.registry import ParserRegistry


def test_registry_routes_h2_view_to_h2_view_parser() -> None:
    registry = build_default_registry()

    assert registry.has_parser("h2_view") is True

    parser = registry.get_parser("h2_view")

    assert isinstance(parser, H2ViewParser)


def test_registry_routes_every_hintco_page_to_hintco_parser() -> None:
    from config import HINTCO_SOURCES

    registry = build_default_registry()

    for source in HINTCO_SOURCES:
        parser = registry.get_parser(source["source_id"])
        assert isinstance(parser, HintcoParser), source["source_id"]


def test_registry_routes_every_hydrogen_council_page_to_its_parser() -> None:
    from config import HYDROGEN_COUNCIL_SOURCES

    registry = build_default_registry()

    for source in HYDROGEN_COUNCIL_SOURCES:
        parser = registry.get_parser(source["source_id"])
        assert isinstance(parser, HydrogenCouncilParser), source["source_id"]


def test_registry_returns_none_for_unregistered_source() -> None:
    registry = build_default_registry()

    # The bare collector-level IDs are not themselves registered — only
    # the concrete per-page source_ids are (see the two tests above).
    assert registry.has_parser("hintco") is False
    assert registry.has_parser("hydrogen_council") is False
    assert registry.get_parser("does_not_exist") is None


def test_registry_register_and_get_are_independent_instances() -> None:
    registry = ParserRegistry()
    registry.register("h2_view", H2ViewParser)

    first = registry.get_parser("h2_view")
    second = registry.get_parser("h2_view")

    assert first is not second
    assert isinstance(first, H2ViewParser)
