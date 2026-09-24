from gmip.parsers.base_parser import (
    BaseParser,
    ParserError,
    ParserValidationError,
)
from gmip.parsers.h2_view_parser import H2ViewParser
from gmip.parsers.hintco_parser import HintcoParser
from gmip.parsers.hydrogen_council_parser import HydrogenCouncilParser
from gmip.parsers.registry import ParserRegistry


def build_default_registry() -> ParserRegistry:
    """
    Build the ParserRegistry wired up with every real structured parser.

    Hintco and Hydrogen Council each expose several page-level source_ids
    (see config.HINTCO_SOURCES / config.HYDROGEN_COUNCIL_SOURCES at the
    project root) that all route to the same parser class, which branches
    internally on the exact source_id. Imported lazily so importing
    gmip.parsers never requires the legacy root config module unless this
    function is actually called.
    """
    registry = ParserRegistry()
    registry.register("h2_view", H2ViewParser)

    from config import HINTCO_SOURCES, HYDROGEN_COUNCIL_SOURCES

    for source in HINTCO_SOURCES:
        registry.register(source["source_id"], HintcoParser)

    for source in HYDROGEN_COUNCIL_SOURCES:
        registry.register(source["source_id"], HydrogenCouncilParser)

    return registry


__all__ = [
    "BaseParser",
    "ParserError",
    "ParserValidationError",
    "H2ViewParser",
    "HintcoParser",
    "HydrogenCouncilParser",
    "ParserRegistry",
    "build_default_registry",
]
