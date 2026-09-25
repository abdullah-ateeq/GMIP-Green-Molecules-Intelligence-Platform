import { Newspaper } from 'lucide-react'
import { api, type IntelligenceItem } from '../../lib/api'
import { useFetch } from '../../lib/useFetch'
import { timeAgo } from '../../lib/utils'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { Skeleton } from '../ui/Skeleton'
import { StatusChip, statusToTone } from '../ui/StatusChip'

const TYPE_LABELS: Record<string, string> = {
  tender: 'TENDER',
  news: 'NEWS',
  report: 'REPORT',
  member_update: 'MEMBERSHIP',
  company_update: 'COMPANY',
  policy: 'POLICY',
  project: 'PROJECT',
}

function IntelligenceRow({ item }: { item: IntelligenceItem }) {
  const meta = [item.countries[0], item.products[0]].filter(Boolean).join(' · ')

  return (
    <a
      href={item.source_url}
      target="_blank"
      rel="noreferrer"
      className="block rounded-lg border border-transparent px-3 py-3 transition-colors hover:border-border hover:bg-surface-2"
    >
      <div className="mb-1.5 flex items-center gap-2">
        <span className="rounded border border-aqua/25 bg-aqua/10 px-1.5 py-0.5 text-[10px] font-semibold text-aqua">
          {TYPE_LABELS[item.intelligence_type] ?? item.intelligence_type.toUpperCase()}
        </span>
        {item.categories.map((category) => (
          <span
            key={category}
            className="rounded border border-border px-1.5 py-0.5 text-[10px] text-text-muted"
          >
            {category}
          </span>
        ))}
      </div>

      <p className="text-[13px] font-medium leading-snug text-text-primary">
        {item.title}
      </p>

      {meta && <p className="mt-1 text-xs text-text-muted">{meta}</p>}

      <div className="mt-2 flex items-center gap-3 text-[11px] text-text-muted">
        <span>{timeAgo(item.collected_at)}</span>
        {item.importance && (
          <StatusChip tone={statusToTone(item.importance === 'high' ? 'watch' : undefined)}>
            {item.importance}
          </StatusChip>
        )}
        {item.confidence && <span>Confidence: {item.confidence}</span>}
      </div>
    </a>
  )
}

export function LatestIntelligenceFeed() {
  const { data, loading } = useFetch(() => api.recentIntelligence(12), [])

  return (
    <Card className="h-full">
      <CardHeader>
        <div>
          <CardTitle>Latest Intelligence</CardTitle>
          <CardSubtitle>Most recently collected, across all sources</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent className="max-h-[520px] space-y-1 overflow-y-auto">
        {loading ? (
          <div className="space-y-2">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : !data || data.length === 0 ? (
          <EmptyState
            icon={Newspaper}
            title="No intelligence collected yet"
            subtitle="Run a collection cycle to see structured intelligence appear here."
          />
        ) : (
          data.map((item) => (
            <IntelligenceRow key={item.intelligence_id} item={item} />
          ))
        )}
      </CardContent>
    </Card>
  )
}
