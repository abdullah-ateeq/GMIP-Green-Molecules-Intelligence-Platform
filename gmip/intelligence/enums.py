from enum import Enum


class IntelligenceType(str, Enum):
    REPORT = "report"
    NEWS = "news"
    TENDER = "tender"
    PROJECT = "project"
    POLICY = "policy"
    REGULATION = "regulation"
    MEMBER_UPDATE = "member_update"
    COMPANY_UPDATE = "company_update"
    MARKET_DATA = "market_data"
    VIDEO = "video"
    OFFTAKE = "offtake"
    INVESTMENT = "investment"
    MARKET_METRIC = "market_metric"
    TECHNOLOGY = "technology"
    FUNDING = "funding"
    PORT_INFRASTRUCTURE = "port_infrastructure"
    OTHER = "other"


class IntelligenceStatus(str, Enum):
    NEW = "new"
    UPDATED = "updated"
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class ImportanceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EntityType(str, Enum):
    COMPANY = "company"
    PROJECT = "project"
    COUNTRY = "country"
    CITY = "city"
    PORT = "port"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    PERSON = "person"
    ORGANISATION = "organisation"
    GOVERNMENT = "government"
    REGULATOR = "regulator"
    CERTIFICATION = "certification"
    POLICY = "policy"
    FUNDING_BODY = "funding_body"
    OTHER = "other"


class EventType(str, Enum):
    # Reports / intelligence items
    REPORT_PUBLISHED = "report_published"
    NEW_REPORT = "new_report"
    REPORT_UPDATED = "report_updated"
    NEW_INTELLIGENCE_ITEM = "new_intelligence_item"
    PDF_ADDED = "pdf_added"
    PDF_REPLACED = "pdf_replaced"

    # Tenders / auctions
    TENDER_LAUNCHED = "tender_launched"
    TENDER_UPDATED = "tender_updated"
    NEW_LOT = "new_lot"
    DEADLINE_EXTENDED = "deadline_extended"
    DEADLINE_CHANGED = "deadline_changed"
    ELIGIBILITY_CHANGED = "eligibility_changed"
    AMENDMENT = "amendment"
    TENDER_CANCELLED = "tender_cancelled"
    FUTURE_AUCTION_ANNOUNCED = "future_auction_announced"
    CONTRACT_AWARDED = "contract_awarded"

    # Commercial
    OFFTAKE_SIGNED = "offtake_signed"
    PARTNERSHIP_SIGNED = "partnership_signed"
    FUNDING_APPROVED = "funding_approved"
    FUNDING_SECURED = "funding_secured"

    # Projects
    PROJECT_ANNOUNCED = "project_announced"
    PROJECT_MILESTONE = "project_milestone"
    FID_REACHED = "fid_reached"
    CONSTRUCTION_STARTED = "construction_started"
    COD_REACHED = "cod_reached"
    PROJECT_DELAYED = "project_delayed"
    PROJECT_CANCELLED = "project_cancelled"
    PLANT_COMMISSIONED = "plant_commissioned"

    # Policy / regulation
    POLICY_ADOPTED = "policy_adopted"
    POLICY_UPDATE = "policy_update"
    REGULATION_UPDATED = "regulation_updated"
    CERTIFICATION_UPDATED = "certification_updated"

    # Membership / organisation
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    MEMBERSHIP_SIGNAL = "membership_signal"
    BOARD_CHANGE = "board_change"
    EXECUTIVE_APPOINTED = "executive_appointed"

    # Market / technology
    MARKET_STATISTIC_UPDATE = "market_statistic_update"
    TECHNOLOGY_SELECTED = "technology_selected"

    OTHER = "other"