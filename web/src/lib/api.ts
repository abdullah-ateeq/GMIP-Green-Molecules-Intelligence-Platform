export interface DashboardSummary {
  opportunities: number
  latest_changes: number
  monitored_sources: number
  last_scan: string | null
  run_status: string
  sources_checked: number
  sources_changed: number
  errors_count: number
}

export interface IntelligenceItem {
  intelligence_id: string
  source_id: string
  source_organisation: string
  parser_name: string | null
  intelligence_type: string
  title: string
  summary: string | null
  source_url: string
  published_at: string | null
  products: string[]
  countries: string[]
  companies: string[]
  categories: string[]
  collected_at: string
  confidence: string | null
  importance: string | null
  why_it_matters: string | null
  tender_status: string | null
  tender_region: string | null
  offtake_product: string | null
  offtake_volume: string | null
  offtake_duration: string | null
  // null = source_url has never been checked (the honest default).
  source_available: boolean | null
  source_status: string | null
  source_http_status: number | null
}

export interface SourceStatus {
  source_id: string
  source_name: string
  organization: string
  access_mode: string
  source_category: string
  enabled: number
  license_required: number
  last_attempted_at: string | null
  last_successful_at: string | null
  last_status: string | null
  last_error: string | null
  failure_count: number
  freshness: 'CURRENT' | 'STALE' | 'VERY_STALE' | 'NEVER_COLLECTED'
  implementation_status: 'HEALTHY' | 'NEEDS_ATTENTION'
  access_status: 'NORMAL' | 'BLOCKED'
}

export interface CountryMention {
  country: string
  mentions: number
}

export interface CategoryCount {
  source_organisation?: string
  intelligence_type?: string
  total: number
}

export interface ActivityPoint {
  day: string
  total: number
}

export interface TenderCounts {
  open: number
  closed: number
  total: number
}

export interface CollectorResultSummary {
  source_id: string
  source_name: string
  status: string
  message: string
  error: string | null
}

export interface CollectRunResult {
  duration_seconds: number
  sources_checked: number
  errors_count: number
  results: CollectorResultSummary[]
}

export interface BusinessKpis {
  new_intelligence_total: number
  new_intelligence_7d: number
  open_opportunities: number
  closed_opportunities: number
  fid_count_30d: number
  offtake_count_30d: number
  offtake_total: number
}

export interface ActivitySeriesPoint {
  day: string
  projects: number
  tenders: number
  offtake: number
  fid: number
  policy: number
}

export interface SourceCategoryCount {
  source_category: string
  total: number
}

export interface OpportunityRadarItem {
  intelligence_id: string
  title: string
  source_url: string
  product: string | null
  country: string | null
  stage: string
  deadline: string | null
  relevance: number
  priority: 'High' | 'Medium' | 'Low'
  collected_at: string
  source_available: boolean | null
}

export interface MarketSignal {
  signal_type: string
  message: string
  region: string
  confidence: number
  supporting_event_count: number
  supporting_intelligence_ids: string[]
}

export interface EntitySummary {
  entity_id: string
  entity_type: 'COMPANY' | 'PROJECT'
  canonical_name: string
  aliases: string[]
  country: string | null
  description: string | null
  created_at: string
  updated_at: string
}

export interface EntityRelationship {
  relationship_id: string
  subject_entity_id: string
  relationship_type: string
  object_entity_id: string
  source_intelligence_object_id: string | null
  confidence: number
  first_seen_at: string
  last_seen_at: string
}

export interface EntityMentionSummary {
  intelligence_object_id: string
  title: string
  source_url: string
  intelligence_type: string
  collected_at: string
  original_mention: string
}

export interface EntityProfile {
  entity: EntitySummary
  mention_count: number
  countries: string[]
  products: string[]
  latest_intelligence: EntityMentionSummary[]
  relationships: EntityRelationship[]
}

const BASE = '/api'

async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`)

  if (!response.ok) {
    throw new Error(`Request to ${path} failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

async function postJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { method: 'POST' })

  if (!response.ok) {
    throw new Error(`Request to ${path} failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

export const api = {
  dashboardSummary: () => getJSON<DashboardSummary>('/dashboard/summary'),
  recentIntelligence: (limit = 20) =>
    getJSON<IntelligenceItem[]>(`/intelligence/recent?limit=${limit}`),
  sources: () => getJSON<SourceStatus[]>('/sources'),
  countryMentions: (limit = 15) =>
    getJSON<CountryMention[]>(`/analytics/countries?limit=${limit}`),
  sourceTypeDistribution: () =>
    getJSON<CategoryCount[]>('/analytics/source-types'),
  intelligenceTypeDistribution: () =>
    getJSON<CategoryCount[]>('/analytics/intelligence-types'),
  activity: (days = 30) =>
    getJSON<ActivityPoint[]>(`/analytics/activity?days=${days}`),
  intelligenceCount: (sinceDays?: number) =>
    getJSON<{ total: number }>(
      `/analytics/intelligence-count${sinceDays ? `?since_days=${sinceDays}` : ''}`,
    ),
  tenderCounts: () => getJSON<TenderCounts>('/analytics/tenders'),
  collectRun: () => postJSON<CollectRunResult>('/collect/run'),
  businessKpis: () => getJSON<BusinessKpis>('/business/kpis'),
  businessActivity: (days = 30) =>
    getJSON<ActivitySeriesPoint[]>(`/business/activity?days=${days}`),
  businessSourceCategories: () =>
    getJSON<SourceCategoryCount[]>('/business/source-categories'),
  businessOpportunities: (limit = 20) =>
    getJSON<OpportunityRadarItem[]>(`/business/opportunities?limit=${limit}`),
  businessSignals: () => getJSON<MarketSignal[]>('/business/signals'),
  companies: (limit = 200) =>
    getJSON<EntitySummary[]>(`/entities/companies?limit=${limit}`),
  companyDetail: (entityId: string) =>
    getJSON<EntityProfile>(`/entities/companies/${entityId}`),
  projects: (limit = 200) =>
    getJSON<EntitySummary[]>(`/entities/projects?limit=${limit}`),
  projectDetail: (entityId: string) =>
    getJSON<EntityProfile>(`/entities/projects/${entityId}`),
  searchEntities: (query: string, entityType?: 'COMPANY' | 'PROJECT') =>
    getJSON<EntitySummary[]>(
      `/entities/search?q=${encodeURIComponent(query)}${entityType ? `&entity_type=${entityType}` : ''}`,
    ),
}
