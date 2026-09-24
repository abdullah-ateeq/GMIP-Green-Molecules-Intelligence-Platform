from __future__ import annotations

from enum import Enum


class SourceAccessMode(str, Enum):
    PUBLIC_HTML = "public_html"
    PUBLIC_RSS = "public_rss"
    PUBLIC_API = "public_api"
    LICENSED_API = "licensed_api"
    LICENSED_FEED = "licensed_feed"
    DISCOVERY_ONLY = "discovery_only"
    MANUAL_IMPORT = "manual_import"
    DISABLED_PENDING_LICENSE = "disabled_pending_license"


class SourceCategory(str, Enum):
    OFFICIAL_PROCUREMENT = "official_procurement"
    INDUSTRY_BODY = "industry_body"
    INDUSTRY_MEDIA = "industry_media"
    PREMIUM_MARKET_DATA = "premium_market_data"
