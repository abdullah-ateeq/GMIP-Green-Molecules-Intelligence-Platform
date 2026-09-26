# GMIP — Green Molecules Intelligence Platform

**A market-intelligence and decision-support platform for the global green hydrogen, green ammonia, and renewable methanol industry.**

GMIP monitors official tender sources, industry bodies, and market media; converts what it collects into structured, source-independent intelligence; and is built to eventually help a business-development team answer questions like *"which projects reached FID this month?"* or *"what new offtake opportunities appeared this week?"* — not just *"what pages changed."*

> GMIP is not a news aggregator or a generic web scraper. It is designed to become the kind of decision-support terminal a commercial team can actually run a business on.

---

## Table of Contents

- [Vision](#vision)
- [Current Status](#current-status)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Data Sources & Access Governance](#data-sources--access-governance)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Team](#team)
- [License](#license)

---

## Vision

The platform started narrowly, monitoring **Hintco** (the H2Global mechanism's tender and auction operator) for procurement opportunities, and is expanding into a multi-source intelligence engine covering:

- Green Hydrogen, Green Ammonia, Renewable/e-Methanol, RFNBO fuels
- Tenders, auctions, and procurement opportunities
- Project announcements, FIDs, and investment activity
- Market direction, policy, and industry positioning
- Offtake agreements and commercial partnerships

The guiding architectural principle: **every source-specific collector translates its content into a common, source-independent intelligence model.** GMIP is not being built as "a Hintco app" plus "a Hydrogen Council app" — each website is simply a source feeding one shared intelligence engine, so the platform can grow from a handful of sources to dozens without a rewrite.

## Current Status

GMIP is under active daily development. The collection foundation is mature; the deeper intelligence layers (entity resolution, knowledge graph, signal detection, AI reasoning) are still ahead.

| Component | Status |
|---|---|
| Source collectors (Hintco, Hydrogen Council) | ✅ Working |
| `RawDocument` model | ✅ Complete |
| `BaseParser` abstraction | ✅ Complete |
| `IntelligenceObject` schema | ✅ Complete (tender & offtake structures included) |
| Structured Hintco parser (tender lots, news events) | ✅ Working |
| Structured Hydrogen Council parser (reports, newsroom, strategic intelligence) | ✅ Working |
| H2 View collector & parser (page-based, via gasworld.com) | ✅ Working |
| Parser registry (source → parser routing) | ✅ Working |
| Source access-mode governance (public / licensed / pending) | ✅ Working |
| Source health tracking & persistence | ✅ Working |
| Licensed-source connectors (Hydrogen Insight, Recharge News, S&P Global, Argus) | 🟡 Adapter ready, pending credentials |
| Desktop application (PySide6) | 🟡 Dashboard & source selection working; several tabs still placeholders |
| Streamlit dashboard | ✅ Working |
| Web dashboard (React + FastAPI, "Carbon Green Terminal") | 🟡 Executive Dashboard working end-to-end on real data; deeper pages (Projects, Companies, Policy, AI Assistant, Reports) not yet built |
| Entity resolution / knowledge graph / signal engine | ⬜ Planned |
| Automated scheduling & alerts | ⬜ Planned |

## Architecture

GMIP currently runs two pipelines side by side, by design, while the platform migrates incrementally without breaking what already works.

**Legacy operational pipeline** (proven, still authoritative for change detection):

```
Source → Download → Extract Text → Keyword Classification
       → Hash Comparison → CHANGED / NO_CHANGE → SQLite → Excel Report
```

**New structured-intelligence pipeline** (additive, running alongside the legacy path):

```
Source → Collector → RawDocument → Source-Specific Parser
       → IntelligenceObject → SQLite (intelligence_objects) → Query / UI
```

Every parsed `IntelligenceObject` carries products, countries, companies, structured tender/offtake details, events, and full provenance back to its source document. Parser failures are isolated — they can never break the legacy collection path they run alongside.

## Project Structure

```
GMIP/
├── app.py                    # CLI entry point — runs the full collection cycle
├── dashboard.py               # Streamlit read-only dashboard
├── config.py                  # Legacy source configuration & keyword libraries
├── database.py                # SQLite schema & data access (legacy + new tables)
├── hintco_collector.py        # Legacy collection + structured-parsing integration hook
├── models.py                  # Legacy result dataclasses
├── collectors/                # Modular collector layer (Hintco, Hydrogen Council)
├── UI/                        # PySide6 desktop application
├── api/                       # FastAPI read-only API layer, serving the web dashboard
├── web/                       # React + TypeScript web dashboard ("Carbon Green Terminal")
├── gmip/                      # New-architecture intelligence platform package
│   ├── models/                 # RawDocument
│   ├── parsers/                 # BaseParser, ParserRegistry, and per-source parsers
│   ├── intelligence/            # IntelligenceObject, entities, events, enums
│   ├── config/                  # SourceDefinition, SourceAccessMode, source registry
│   ├── collectors/               # New-architecture collectors (H2 View, licensed connectors)
│   └── tests/                    # Test suite (pytest)
├── Data/Raw/                  # Collected raw snapshots (git-ignored)
└── Output/                    # Generated reports (git-ignored)
```

## Getting Started

### Prerequisites

- Python **3.10+** (developed and tested on 3.12)
- pip

### Installation

```bash
git clone https://github.com/abdullah-ateeq/GMIP-Green-Molecules-Intelligence-Platform.git
cd GMIP-Green-Molecules-Intelligence-Platform

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

# Optional — only needed for the web dashboard
cd web && npm install && cd ..
```

Create a `.env` file for local configuration (and, when available, licensed-source API credentials):

```bash
APP_ENV=development

# Licensed-source credentials (optional — connectors stay inactive until set)
# Setting both URL + KEY makes the connector start calling the endpoint, but
# it still won't produce any intelligence until a record_mapper matching that
# provider's real API response schema is supplied — see
# gmip/collectors/licensed_connector.py for why.
# HYDROGEN_INSIGHT_API_URL=
# HYDROGEN_INSIGHT_API_KEY=
# RECHARGE_NEWS_API_URL=
# RECHARGE_NEWS_API_KEY=
# SP_GLOBAL_API_URL=
# SP_GLOBAL_API_KEY=
# ARGUS_API_URL=
# ARGUS_API_KEY=
```

## Usage

**Run a full collection cycle** (populates SQLite and exports an Excel report):

```bash
python app.py
```

**Launch the Streamlit dashboard:**

```bash
streamlit run dashboard.py
```

**Launch the desktop application:**

```bash
python UI/run_ui.py
```

**Launch the web dashboard** (API + frontend, two terminals):

```bash
uvicorn api.main:app --port 8000        # backend, from the project root
cd web && npm run dev                    # frontend, http://localhost:5173
```

## Data Sources & Access Governance

GMIP explicitly distinguishes between source access modes, and never scrapes a source outside what it's actually entitled to:

| Source | Role | Access Mode |
|---|---|---|
| Hintco | Transactional / procurement intelligence | Public |
| Hydrogen Council | Strategic / market intelligence | Public |
| H2 View | Secondary discovery media | Public (page collection — h2-view.com and its RSS feed are both dead; H2 View now publishes as a channel page on gasworld.com) |
| Hydrogen Insight | Secondary media | Licensed — pending credentials |
| Recharge News | Secondary media | Licensed — pending credentials |
| S&P Global Commodity Insights | Premium market data | Licensed API — pending credentials |
| Argus Media | Premium market data | Licensed API — pending credentials |

Sources requiring a licence or credentials are represented in the platform's configuration and source-health tracking, but their connectors make **no network requests at all** until real credentials are supplied — this is enforced structurally, not just by convention.

## Testing

```bash
pytest -q
```

The suite covers the `RawDocument`/`BaseParser`/`IntelligenceObject` models, every structured parser (against patterns drawn from real collected content), the parser registry, source-health persistence, and regression checks on the legacy collectors.

## Roadmap

Near-term priorities, in order:

1. Entity resolution (canonicalizing company/project/country names across sources)
2. Intelligence database expansion (entities, events, relationships)
3. Knowledge graph
4. Signal engine (cross-source pattern detection)
5. Remaining web dashboard pages (Projects, Companies, Policy, Intelligence Feed, AI Assistant, Reports)
6. AI-assisted reasoning over structured intelligence
7. Automated scheduling & alerting
8. Additional global sources

## Team

- **Muhammad Ameer Hamza** — Concept, product vision & domain strategy
- **Abdullah Ateeq** — Lead developer

## License

Proprietary — All rights reserved. This repository and its contents are not licensed for external use, reproduction, or distribution without explicit permission.
