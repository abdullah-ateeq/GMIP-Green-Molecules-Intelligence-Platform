from __future__ import annotations

from gmip.config.access_mode import SourceAccessMode, SourceCategory
from gmip.config.source_definition import SourceDefinition

SOURCE_REGISTRY: list[SourceDefinition] = [
    SourceDefinition(
        source_id="hintco",
        source_name="Hintco",
        organization="Hintco",
        source_category=SourceCategory.OFFICIAL_PROCUREMENT,
        access_mode=SourceAccessMode.PUBLIC_HTML,
        base_url="https://hintco.eu/",
        enabled=True,
        priority=1,
        authority_level="PRIMARY",
        intelligence_role="TRANSACTIONAL_PROCUREMENT_INTELLIGENCE",
        collector_id="hintco",
        collection_frequency="daily",
        terms_note=(
            "Official public tender/auction pages. Legacy keyword-based "
            "classification only in this phase; no structured parser yet."
        ),
    ),
    SourceDefinition(
        source_id="hydrogen_council",
        source_name="Hydrogen Council",
        organization="Hydrogen Council",
        source_category=SourceCategory.INDUSTRY_BODY,
        access_mode=SourceAccessMode.PUBLIC_HTML,
        base_url="https://hydrogencouncil.com/en/",
        enabled=True,
        priority=2,
        authority_level="STRATEGIC",
        intelligence_role="STRATEGIC_MARKET_INTELLIGENCE",
        collector_id="hydrogen_council",
        collection_frequency="daily",
        terms_note=(
            "Public industry-body pages. Currently classified with the same "
            "legacy Hintco keyword vocabulary as Hintco (known architecture "
            "drift, fix deferred to a future phase)."
        ),
    ),
    SourceDefinition(
        source_id="h2_view",
        source_name="H2 View",
        organization="H2 View",
        source_family="industry_media",
        source_category=SourceCategory.INDUSTRY_MEDIA,
        access_mode=SourceAccessMode.PUBLIC_RSS,
        base_url="https://www.h2-view.com/",
        feed_url="https://www.h2-view.com/feed/",
        enabled=True,
        priority=3,
        authority_level="SECONDARY",
        intelligence_role="DISCOVERY_SECONDARY_INTELLIGENCE",
        parser_id="h2_view",
        collector_id="h2_view",
        collection_frequency="hourly",
        terms_note="Public RSS feed. No AI-crawler restriction found in robots.txt.",
    ),
    SourceDefinition(
        source_id="hydrogen_insight",
        source_name="Hydrogen Insight",
        organization="DN Media Group",
        source_family="industry_media",
        source_category=SourceCategory.INDUSTRY_MEDIA,
        access_mode=SourceAccessMode.DISABLED_PENDING_LICENSE,
        base_url="https://www.hydrogeninsight.com/",
        requires_auth=True,
        license_required=True,
        enabled=False,
        priority=3,
        authority_level="SECONDARY",
        intelligence_role="DISCOVERY_SECONDARY_INTELLIGENCE",
        parser_id="licensed_media",
        collector_id="hydrogen_insight",
        collection_frequency="daily",
        terms_note=(
            "robots.txt explicitly names and disallows AI/LLM crawlers "
            "(including Claude). Public-site scraping is out regardless of "
            "licensing status. Data-licensing agreement with DN Media Group "
            "reported as in progress; connector activates once a real "
            "feed/API endpoint and credentials are supplied via .env."
        ),
    ),
    SourceDefinition(
        source_id="recharge_news",
        source_name="Recharge News",
        organization="DN Media Group",
        source_family="industry_media",
        source_category=SourceCategory.INDUSTRY_MEDIA,
        access_mode=SourceAccessMode.DISABLED_PENDING_LICENSE,
        base_url="https://www.rechargenews.com/",
        requires_auth=True,
        license_required=True,
        enabled=False,
        priority=3,
        authority_level="SECONDARY",
        intelligence_role="DISCOVERY_SECONDARY_INTELLIGENCE",
        parser_id="licensed_media",
        collector_id="recharge_news",
        collection_frequency="daily",
        terms_note=(
            "Same publisher and restriction as Hydrogen Insight (DN Media "
            "Group) — robots.txt explicitly disallows AI/LLM crawlers. "
            "Connector activates once a real feed/API endpoint and "
            "credentials are supplied via .env."
        ),
    ),
    SourceDefinition(
        source_id="sp_global_commodity_insights",
        source_name="S&P Global Commodity Insights",
        organization="S&P Global",
        source_category=SourceCategory.PREMIUM_MARKET_DATA,
        access_mode=SourceAccessMode.LICENSED_API,
        base_url="https://www.spglobal.com/commodityinsights/",
        requires_auth=True,
        license_required=True,
        enabled=False,
        priority=4,
        authority_level="PREMIUM",
        intelligence_role="MARKET_PRICING_INTELLIGENCE",
        parser_id="sp_global",
        collector_id="sp_global_commodity_insights",
        collection_frequency="daily",
        terms_note=(
            "Premium commercial price-assessment product. Public web access "
            "is edge-blocked (robots.txt fetch itself returned HTTP 403). "
            "Connector activates once API endpoint + credentials are "
            "supplied via .env — never scrapes the public site."
        ),
    ),
    SourceDefinition(
        source_id="argus_media",
        source_name="Argus Media",
        organization="Argus Media",
        source_category=SourceCategory.PREMIUM_MARKET_DATA,
        access_mode=SourceAccessMode.LICENSED_API,
        base_url="https://www.argusmedia.com/",
        requires_auth=True,
        license_required=True,
        enabled=False,
        priority=4,
        authority_level="PREMIUM",
        intelligence_role="MARKET_PRICING_INTELLIGENCE",
        parser_id="argus",
        collector_id="argus_media",
        collection_frequency="daily",
        terms_note=(
            "Premium commercial price-assessment product (like S&P). "
            "Connector activates once API/feed endpoint + credentials are "
            "supplied via .env — never scrapes the public site."
        ),
    ),
]


def get_source_definition(source_id: str) -> SourceDefinition | None:
    for source in SOURCE_REGISTRY:
        if source.source_id == source_id:
            return source

    return None
