import { Radar } from 'lucide-react'
import { api } from '../../lib/api'
import { useFetch } from '../../lib/useFetch'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { Skeleton } from '../ui/Skeleton'
import { StatusChip, type ChipTone } from '../ui/StatusChip'

const PRIORITY_TONE: Record<string, ChipTone> = {
  High: 'positive',
  Medium: 'watch',
  Low: 'neutral',
}

export function OpportunityRadar() {
  const { data, loading } = useFetch(() => api.businessOpportunities(20), [])

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Opportunity Radar</CardTitle>
          <CardSubtitle>Open, structured tender and procurement opportunities</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-40 w-full" />
        ) : !data || data.length === 0 ? (
          <EmptyState
            icon={Radar}
            title="No active opportunities detected"
            subtitle="Structured, open tender intelligence from Hintco will appear here once collected."
          />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                <th className="pb-2 font-semibold">Opportunity</th>
                <th className="pb-2 font-semibold">Country</th>
                <th className="pb-2 font-semibold">Molecule</th>
                <th className="pb-2 font-semibold">Stage</th>
                <th className="pb-2 font-semibold">Deadline</th>
                <th className="pb-2 font-semibold">Relevance</th>
                <th className="pb-2 text-right font-semibold">Priority</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr
                  key={item.intelligence_id}
                  className="border-t border-border/60 [&>td]:py-2.5"
                >
                  <td className="max-w-[200px] truncate font-medium text-text-primary">
                    {item.source_available === false ? (
                      <span
                        className="text-text-muted"
                        title="Original source currently unavailable (404/410)."
                      >
                        {item.title}
                      </span>
                    ) : (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-aqua"
                      >
                        {item.title}
                      </a>
                    )}
                  </td>
                  <td className="text-text-secondary">{item.country ?? '—'}</td>
                  <td className="text-text-secondary">{item.product ?? '—'}</td>
                  <td className="text-text-secondary">{item.stage}</td>
                  <td className="text-text-secondary">{item.deadline ?? '—'}</td>
                  <td className="text-text-secondary">{item.relevance}</td>
                  <td className="text-right">
                    <StatusChip tone={PRIORITY_TONE[item.priority] ?? 'neutral'}>
                      {item.priority}
                    </StatusChip>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  )
}
