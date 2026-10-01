"""
Centralized entity-name normalization (section 7 of the entity-resolution
brief): one shared utility, not per-source cleanup. Produces a comparison
KEY used only for matching — canonical_name (the real display name) is
never derived from, or replaced by, this normalized form.

Deliberately conservative: only strips a single trailing, well-known
corporate suffix, never does substring/contains matching, and never
touches the "core" of a name. "Total" and "TotalEnergies" must never
collapse to the same key — and they don't, since there's no space-
separated suffix to strip from a compound word like "TotalEnergies".
"""
from __future__ import annotations

import re
import unicodedata

# Suffixes are matched as whole trailing words (with a preceding space),
# never as a bare substring — so "Shell Trading" is not "Shell" + a
# suffix, and "Grouped Technologies" doesn't get mangled by "group".
_LEGAL_SUFFIXES = (
    "company",
    "co",
    "corporation",
    "corp",
    "incorporated",
    "inc",
    "limited",
    "ltd",
    "plc",
    "llc",
    "gmbh",
    "sa",
    "ag",
    "international",
    "group",
    "holdings",
    "holding",
)


def _base_clean(name: str) -> str:
    cleaned = unicodedata.normalize("NFKC", name or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[.,]", "", cleaned)
    return cleaned.casefold()


def normalize_company_name(name: str) -> str:
    """
    Comparison key for company-name matching. Strips at most ONE
    trailing legal-form suffix (so "ACWA Power Company" and "ACWA Power
    International" both normalize to "acwa power", matching the real
    canonical entity) and never removes anything else.
    """
    lowered = _base_clean(name)
    words = lowered.split(" ")

    if len(words) > 1 and words[-1] in _LEGAL_SUFFIXES:
        words = words[:-1]

    return " ".join(words)


def normalize_project_name(name: str) -> str:
    """
    Comparison key for project-name matching. Deliberately lighter-touch
    than company normalization — project names don't carry legal-form
    suffixes the same way, and over-normalizing here risks collapsing
    genuinely distinct projects (see the entity-resolution brief's
    repeated "do not merge on title similarity alone" warning, honored
    at the resolver level via country-aware matching, not here).
    """
    return _base_clean(name)
