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
}
