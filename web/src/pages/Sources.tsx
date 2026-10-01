import { Database } from 'lucide-react'
import { api, type SourceStatus } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import { timeAgo } from '../lib/utils'
import { Card, CardContent } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'
import { StatusChip, type ChipTone } from '../components/ui/StatusChip'

const CATEGORY_LABELS: Record<string, string> = {
  official_procurement: 'Procurement',
  industry_body: 'Industry Body',
  industry_media: 'Media / Discovery',
  premium_market_data: 'Premium Data',
}

const FRESHNESS_LABELS: Record<SourceStatus['freshness'], string> = {
  CURRENT: 'Current',
  STALE: 'Stale',
  VERY_STALE: 'Very stale',
  NEVER_COLLECTED: 'Never collected',
}

const FRESHNESS_TONE: Record<SourceStatus['freshness'], ChipTone> = {
  CURRENT: 'positive',
  STALE: 'watch',
  VERY_STALE: 'risk',
  NEVER_COLLECTED: 'neutral',
}

function implementationTone(source: SourceStatus): ChipTone {
  return source.implementation_status === 'HEALTHY' ? 'positive' : 'risk'
}

function accessTone(source: SourceStatus): ChipTone {
  return source.access_status === 'BLOCKED' ? 'watch' : 'positive'
}

function SourceRow({ source }: { source: SourceStatus }) {
  return (
    <tr className="border-t border-border/60 [&>td]:py-3 [&>td]:align-top">
      <td>
        <p className="font-medium text-text-primary">{source.source_name}</p>
        <p className="text-xs text-text-muted">{source.organization}</p>
      </td>
      <td className="text-text-secondary">
        {CATEGORY_LABELS[source.source_category] ?? source.source_category}
      </td>
      <td>
        <StatusChip tone={implementationTone(source)}>
          {source.implementation_status === 'HEALTHY' ? 'Healthy' : 'Needs attention'}
        </StatusChip>
      </td>
      <td>
        {source.enabled ? (
          <StatusChip tone={accessTone(source)}>
            {source.access_status === 'BLOCKED' ? 'Blocked' : 'Normal'}
          </StatusChip>
        ) : (
          <StatusChip tone="neutral">
            {source.license_required ? 'Pending license' : 'Disabled'}
          </StatusChip>
        )}
      </td>
      <td>
        <StatusChip tone={FRESHNESS_TONE[source.freshness]}>
          {FRESHNESS_LABELS[source.freshness]}
        </StatusChip>
      </td>
      <td className="text-text-secondary">
        {source.last_successful_at ? timeAgo(source.last_successful_at) : '—'}
      </td>
      <td className="max-w-[260px] truncate text-text-muted" title={source.last_error ?? undefined}>
        {source.last_status === 'BLOCKED_BY_ACCESS_CONTROL'
          ? 'Blocked by access control (e.g. Cloudflare) — will retry on the next scheduled collection.'
          : source.last_error ?? '—'}
      </td>
    </tr>
  )
}

export function Sources() {
  const { data, loading } = useFetch(() => api.sources(), [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold text-text-primary">Sources</h1>
        <p className="mt-1 text-sm text-text-muted">
          Implementation health, live access state, and freshness — kept separate, so a
          temporary access block never reads as a broken collector.
        </p>
      </div>

      <Card>
        <CardContent className="pt-5">
          {loading ? (
            <div className="space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : !data || data.length === 0 ? (
            <EmptyState
              icon={Database}
              title="No sources registered"
              subtitle="Source registry has not been synced yet."
            />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                  <th className="pb-2 font-semibold">Source</th>
                  <th className="pb-2 font-semibold">Category</th>
                  <th className="pb-2 font-semibold">Implementation</th>
                  <th className="pb-2 font-semibold">Live Access</th>
                  <th className="pb-2 font-semibold">Freshness</th>
                  <th className="pb-2 font-semibold">Last Success</th>
                  <th className="pb-2 font-semibold">Note</th>
                </tr>
              </thead>
              <tbody>
                {data.map((source) => (
                  <SourceRow key={source.source_id} source={source} />
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
