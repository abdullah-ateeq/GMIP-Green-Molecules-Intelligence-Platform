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
    REPORT_PUBLISHED = "report_published"
    TENDER_LAUNCHED = "tender_launched"
    DEADLINE_EXTENDED = "deadline_extended"
    CONTRACT_AWARDED = "contract_awarded"
    OFFTAKE_SIGNED = "offtake_signed"
    PROJECT_ANNOUNCED = "project_announced"
    FID_REACHED = "fid_reached"
    CONSTRUCTION_STARTED = "construction_started"
    PROJECT_DELAYED = "project_delayed"
    PROJECT_CANCELLED = "project_cancelled"
    PLANT_COMMISSIONED = "plant_commissioned"
    FUNDING_APPROVED = "funding_approved"
    POLICY_ADOPTED = "policy_adopted"
    REGULATION_UPDATED = "regulation_updated"
    CERTIFICATION_UPDATED = "certification_updated"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    EXECUTIVE_APPOINTED = "executive_appointed"
    TECHNOLOGY_SELECTED = "technology_selected"
    OTHER = "other"