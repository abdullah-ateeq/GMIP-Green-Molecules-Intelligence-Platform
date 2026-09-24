from __future__ import annotations

import sys
from pathlib import Path

# The legacy collectors live at the project root (not under gmip/), and
# import each other with bare `from config import ...` style imports rather
# than package-relative ones. Ensure the project root is importable here
# regardless of how pytest was invoked.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from collectors.hintco_collector import HintcoCollector  # noqa: E402
from collectors.hydrogen_council_collector import (  # noqa: E402
    HydrogenCouncilCollector,
)


def test_hintco_collector_configuration_still_valid() -> None:
    """
    Regression check: this phase's changes must not break the one fully
    working collection path (Hintco), even though no scraping happens in
    this test.
    """
    collector = HintcoCollector()
    is_valid, message = collector.validate_configuration()

    assert is_valid is True, message
    assert collector.source_count == 10


def test_hydrogen_council_collector_configuration_still_valid() -> None:
    collector = HydrogenCouncilCollector()
    is_valid, message = collector.validate_configuration()

    assert is_valid is True, message
    assert collector.source_count == 5
