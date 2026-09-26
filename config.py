"""Central configuration for the Green Molecules Intelligence Platform."""

from __future__ import annotations

import sys
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

# When GMIP runs as normal Python source:
#     BASE_DIR = project folder containing config.py
#
# When GMIP runs as a packaged executable:
#     BASE_DIR = folder containing GMIP.exe
#
# This ensures the database, snapshots and reports remain writable
# and visible beside the packaged application.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent


DATA_DIR = BASE_DIR / "Data"
RAW_DIR = DATA_DIR / "Raw"
SNAPSHOT_DIR = RAW_DIR / "Snapshots"

OUTPUT_DIR = BASE_DIR / "Output"
CHANGES_DIR = OUTPUT_DIR / "Changes"

DATABASE_PATH = BASE_DIR / "hintco_tenders.db"
EXCEL_OUTPUT_PATH = OUTPUT_DIR / "Hintco_Tender.xlsx"


# Create required folders automatically.
for folder in [
    DATA_DIR,
    RAW_DIR,
    SNAPSHOT_DIR,
    OUTPUT_DIR,
    CHANGES_DIR,
]:
    folder.mkdir(parents=True, exist_ok=True)


# ============================================================
# HINTCO SOURCES
# ============================================================

HINTCO_SOURCES = [
    {
        "source_id": "hintco_home",
        "source_name": "Hintco Homepage",
        "url": "https://hintco.eu/",
        "source_type": "Corporate and Market Overview",
        "enabled": True,
    },
    {
        "source_id": "hintco_tenders_overview",
        "source_name": "Hintco Tenders Overview",
        "url": "https://hintco.eu/tenders/",
        "source_type": "Tender Overview",
        "enabled": True,
    },
    {
        "source_id": "hintco_hpa_auctions",
        "source_name": "Hintco HPA Auctions",
        "url": "https://hintco.eu/hpa-auctions/",
        "source_type": "Supply-Side Auction",
        "enabled": True,
    },
    {
        "source_id": "hintco_hsa_auctions",
        "source_name": "Hintco HSA Auctions",
        "url": "https://hintco.eu/hsa-auctions/",
        "source_type": "Demand-Side Auction",
        "enabled": True,
    },
    {
        "source_id": "hintco_tender_1",
        "source_name": "Hintco Tender 1",
        "url": "https://hintco.eu/tender-900m-bmwk/",
        "source_type": "Historical Tender",
        "enabled": True,
    },
    {
        "source_id": "hintco_tender_2",
        "source_name": "Hintco Tender 2",
        "url": "https://hintco.eu/tender-2/",
        "source_type": "Active Tender",
        "enabled": True,
    },
    {
        "source_id": "hintco_tender_2_faq",
        "source_name": "Hintco Tender 2 FAQ",
        "url": "https://hintco.eu/faq-second-h2global-tender/",
        "source_type": "Tender Clarifications",
        "enabled": True,
    },
    {
        "source_id": "hintco_general_faq",
        "source_name": "Hintco General FAQ",
        "url": "https://hintco.eu/frequently-asked-questions/",
        "source_type": "Market and Auction Knowledge",
        "enabled": True,
    },
    {
        "source_id": "hintco_how_to_bid",
        "source_name": "Hintco How to Bid",
        "url": "https://hintco.eu/how-to-bid/",
        "source_type": "Bidder Participation Guidance",
        "enabled": True,
    },
    {
        "source_id": "hintco_news",
        "source_name": "Hintco News",
        "url": "https://hintco.eu/news/",
        "source_type": "News and Market Announcements",
        "enabled": True,
    },
]


# ============================================================
# HYDROGEN COUNCIL SOURCES
# ============================================================

# These sources are consumed by HydrogenCouncilCollector.  Keeping
# them here alongside HINTCO_SOURCES gives every collector the same
# source configuration shape.
HYDROGEN_COUNCIL_SOURCES = [
    {
        "source_id": "hydrogen_council_home",
        "source_name": "Hydrogen Council Homepage",
        "url": "https://hydrogencouncil.com/en/",
        "source_type": "Corporate and Market Overview",
        "enabled": True,
    },
    {
        "source_id": "hydrogen_council_intelligence",
        "source_name": "Hydrogen Council Intelligence",
        "url": "https://hydrogencouncil.com/en/intelligence/",
        "source_type": "Reports and Market Intelligence",
        "enabled": True,
    },
    {
        "source_id": "hydrogen_council_newsroom",
        "source_name": "Hydrogen Council Newsroom",
        "url": "https://hydrogencouncil.com/en/newsroom/",
        "source_type": "News and Market Announcements",
        "enabled": True,
    },
    {
        "source_id": "hydrogen_council_hydrogen_in_action",
        "source_name": "Hydrogen Council Hydrogen in Action",
        "url": "https://hydrogencouncil.com/en/hydrogen-in-action/",
        "source_type": "Projects, Leadership and Deployment Stories",
        "enabled": True,
    },
    {
        "source_id": "hydrogen_council_members",
        "source_name": "Hydrogen Council Members",
        "url": "https://hydrogencouncil.com/en/members/",
        "source_type": "Industry Ecosystem and Membership Intelligence",
        "enabled": True,
    },
]


# ============================================================
# H2 VIEW SOURCES
# ============================================================

# H2 View's own site (h2-view.com) and its RSS feed are dead — H2 View has
# been absorbed into gasworld.com and now publishes as a card-listing
# channel page there. Consumed by H2ViewCollector the same way
# HYDROGEN_COUNCIL_SOURCES is consumed by HydrogenCouncilCollector
# (fetch_page() + HydrogenCouncilParser-style card extraction).
H2_VIEW_SOURCES = [
    {
        "source_id": "h2_view",
        "source_name": "H2 View",
        "url": "https://www.gasworld.com/h2-view/",
        "source_type": "Industry Media - Hydrogen Discovery",
        "enabled": True,
    },
]


# ============================================================
# PRODUCT KEYWORDS
# ============================================================

PRODUCT_KEYWORDS = {
    "RFNBO Hydrogen": [
        "rfnbo hydrogen",
        "renewable hydrogen",
        "green hydrogen",
        "renewable hydrogen supply",
        "clean hydrogen",
        "low-carbon hydrogen",
        "low carbon hydrogen",
    ],

    "RFNBO Ammonia": [
        "rfnbo ammonia",
        "renewable ammonia",
        "green ammonia",
        "renewable ammonia supply",
        "clean ammonia",
        "low-carbon ammonia",
        "low carbon ammonia",
        "e-ammonia",
        "e ammonia",
    ],

    "RFNBO Methanol": [
        "rfnbo methanol",
        "renewable methanol",
        "green methanol",
        "e-methanol",
        "e methanol",
        "electro-methanol",
        "clean methanol",
        "low-carbon methanol",
        "low carbon methanol",
    ],

    "eSAF": [
        "esaf",
        "e-saf",
        "e saf",
        "rfnbo esaf",
        "rfnbo e-saf",
        "synthetic aviation fuel",
        "sustainable aviation fuel",
        "renewable aviation fuel",
        "electro-sustainable aviation fuel",
    ],

    "Hydrogen Derivatives": [
        "hydrogen derivative",
        "hydrogen derivatives",
        "renewable hydrogen derivative",
        "renewable hydrogen derivatives",
        "renewable fuel of non-biological origin",
        "renewable fuels of non-biological origin",
        "rfnbo",
        "rfnbo fuel",
        "rfnbo fuels",
        "green molecule",
        "green molecules",
        "clean product",
        "clean products",
    ],
}


# ============================================================
# COMMERCIAL RELEVANCE KEYWORDS
# ============================================================

# The existing collector uses this list to determine whether
# detected product content is commercially relevant.
#
# The original name is retained to avoid breaking imports,
# although the coverage now includes supply-side, demand-side,
# market, funding, certification and participation intelligence.
SUPPLY_KEYWORDS = [
    # --------------------------------------------------------
    # Auctions and tenders
    # --------------------------------------------------------
    "hpa auction",
    "hpa auctions",
    "hsa auction",
    "hsa auctions",
    "purchase auction",
    "purchase auctions",
    "sales auction",
    "sales auctions",
    "supply-side auction",
    "supply side auction",
    "demand-side auction",
    "demand side auction",
    "double auction",
    "double auctions",
    "tender",
    "tenders",
    "auction",
    "auctions",
    "lot",
    "lots",
    "bilateral tender",
    "global lot",
    "regional lot",

    # --------------------------------------------------------
    # Contracts and counterparties
    # --------------------------------------------------------
    "hydrogen purchase agreement",
    "hydrogen purchase agreements",
    "hydrogen sales agreement",
    "hydrogen sales agreements",
    "purchase agreement",
    "purchase agreements",
    "sales agreement",
    "sales agreements",
    "offtake agreement",
    "offtake agreements",
    "long-term contract",
    "long term contract",
    "short-term contract",
    "short term contract",
    "framework agreement",
    "framework hsa",
    "supplier",
    "suppliers",
    "producer",
    "producers",
    "offtaker",
    "offtakers",
    "buyer",
    "buyers",
    "bidder",
    "bidders",
    "counterparty",
    "counterparties",

    # --------------------------------------------------------
    # Participation process
    # --------------------------------------------------------
    "call for participation",
    "call for supply",
    "invitation to tender",
    "request for proposal",
    "request for quotation",
    "public release phase",
    "application phase",
    "negotiation phase",
    "final bid phase",
    "final binding bid",
    "request to participate",
    "submission deadline",
    "application deadline",
    "eligibility criteria",
    "qualification criteria",
    "prequalification",
    "tender platform",
    "tender agent",
    "tender document",
    "tender documents",
    "auction document",
    "auction documents",
    "contract document",
    "contract documents",
    "performance specification",
    "technical specification",
    "bid evaluation",
    "bid scoring",
    "submission procedure",
    "registration process",

    # --------------------------------------------------------
    # Commercial and market intelligence
    # --------------------------------------------------------
    "procurement",
    "offtake",
    "market maker",
    "market making",
    "price signal",
    "price signals",
    "reference price",
    "market price",
    "willingness to pay",
    "market liquidity",
    "trade flows",
    "cost of difference",
    "funding volume",
    "funding allocation",
    "funding commitment",
    "contract quantity",
    "minimum contract quantity",
    "delivery volume",
    "delivery period",
    "first deliveries",
    "secure purchase agreement",
    "long-term offtake contract",
    "competitive supplier",

    # --------------------------------------------------------
    # Project and investment intelligence
    # --------------------------------------------------------
    "final investment decision",
    "final investment decisions",
    "fid",
    "project implementation",
    "project development",
    "production project",
    "investment security",
    "price security",
    "market security",
    "counterparty security",
    "legal security",

    # --------------------------------------------------------
    # Certification and regulatory intelligence
    # --------------------------------------------------------
    "pre-certification",
    "precertification",
    "certification readiness",
    "certification requirement",
    "rfnbo compliance",
    "sustainability requirement",
    "sustainability requirements",
    "regulatory compliance",
    "voluntary scheme",
    "state aid",
    "eu requirement",
    "eu requirements",
    "eligible country",
    "eligible countries",
    "production region",
    "delivery point",

    # --------------------------------------------------------
    # Funding and government cooperation
    # --------------------------------------------------------
    "funded by",
    "co-fund",
    "co-funded",
    "funding",
    "budget",
    "federal ministry",
    "government funding",
    "funding programme",
    "funding program",
    "jointly committed",
    "financial support",
]


# ============================================================
# EVENT KEYWORDS
# ============================================================

EVENT_KEYWORDS = {
    "NEW_TENDER": [
        "new tender",
        "new auction",
        "launches tender",
        "launched tender",
        "launches auction",
        "launched auction",
        "starts tender",
        "tender launched",
        "auction launched",
        "invitation to tender",
        "call for participation",
        "call for supply",
        "applications are open",
        "application phase opened",
        "registration is open",
    ],

    "APPLICATION_PHASE": [
        "application phase",
        "application phase opened",
        "entered the application phase",
        "request to participate",
        "submit an application",
        "application window",
        "application period",
        "application phase has ended",
        "applications have closed",
    ],

    "NEGOTIATION_PHASE": [
        "negotiation phase",
        "entered negotiations",
        "entered the negotiation phase",
        "advanced negotiation stage",
        "contract negotiations",
        "bilateral negotiations",
    ],

    "FINAL_BID_PHASE": [
        "final bid phase",
        "final binding bid",
        "final binding bids",
        "invited to submit final bids",
        "bid submission phase",
        "binding offer",
        "binding offers",
    ],

    "DEADLINE_UPDATE": [
        "deadline extended",
        "submission deadline",
        "application deadline",
        "extension of deadline",
        "new deadline",
        "deadline postponed",
        "timeline extended",
        "submission period extended",
        "application period extended",
        "closing date",
    ],

    "TENDER_AMENDMENT": [
        "amendment",
        "amended",
        "addendum",
        "updated tender documents",
        "revised tender documents",
        "tender update",
        "auction update",
        "clarification",
        "clarifications",
        "faq updated",
        "updated faq",
        "contract documents updated",
        "performance specification updated",
        "technical specification updated",
        "eligibility criteria updated",
    ],

    "FUNDING_UPDATE": [
        "funding increased",
        "funding allocation",
        "additional funding",
        "budget increased",
        "budget approval",
        "funding commitment",
        "funding volume",
        "allocated to",
        "co-fund",
        "co-funded",
        "jointly committed",
        "financial commitment",
    ],

    "AWARD_NOTICE": [
        "award",
        "awarded",
        "auction result",
        "auction results",
        "tender result",
        "tender results",
        "selected bidder",
        "selected bidders",
        "successful bidder",
        "successful bidders",
        "preferred bidder",
        "preferred bidders",
        "contract signed",
        "contracts signed",
        "supply contract signed",
        "purchase agreement signed",
        "hydrogen purchase agreement signed",
        "hydrogen sales agreement signed",
    ],

    "HSA_DEVELOPMENT": [
        "hsa auction",
        "hsa auctions",
        "sales auction",
        "sales auctions",
        "hydrogen sales agreement",
        "hydrogen sales agreements",
        "framework hsa",
        "framework agreement",
        "offtaker auction",
        "demand-side auction",
        "demand side auction",
        "willingness to pay",
        "short-term sales agreement",
        "short term sales agreement",
    ],

    "CERTIFICATION_UPDATE": [
        "pre-certification",
        "precertification",
        "certification readiness",
        "rfnbo compliance",
        "voluntary scheme",
        "certification requirement",
        "certification requirements",
        "regulatory compliance",
        "sustainability requirement",
        "sustainability requirements",
    ],

    "MARKET_ANNOUNCEMENT": [
        "market consultation",
        "future auction",
        "future auctions",
        "upcoming auction",
        "upcoming auctions",
        "planned auction",
        "planned auctions",
        "bilateral tender",
        "price signal",
        "price signals",
        "reference price",
        "market liquidity",
        "trade flows",
        "market development",
        "market creation",
    ],

    "TENDER_CANCELLATION": [
        "tender cancelled",
        "tender canceled",
        "auction cancelled",
        "auction canceled",
        "lot cancelled",
        "lot canceled",
        "procedure cancelled",
        "procedure canceled",
        "tender suspended",
        "auction suspended",
        "lot suspended",
        "lot reopened",
        "auction reopened",
        "tender reopened",
    ],

    "TENDER_DOCUMENT_UPDATE": [
        "new tender documents",
        "new auction documents",
        "documents published",
        "documents available",
        "fact sheet",
        "factsheet",
        "guidance published",
        "technical specifications published",
        "contract template",
        "download tender documents",
    ],
}


# ============================================================
# HTTP SETTINGS
# ============================================================

REQUEST_TIMEOUT_SECONDS = 45

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
