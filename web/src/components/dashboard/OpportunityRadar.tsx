import { Radar } from 'lucide-react'
import { api } from '../../lib/api'
import { useFetch } from '../../lib/useFetch'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { Skeleton } from '../ui/Skeleton'
import { StatusChip, statusToTone } from '../ui/StatusChip'

export function OpportunityRadar() {
  const { data, loading } = useFetch(() => api.recentIntelligence(50), [])
  const tenders = (data ?? []).filter((item) => item.intelligence_type === 'tender')

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Opportunity Radar</CardTitle>
          <CardSubtitle>Open and recently tracked tender opportunities</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-40 w-full" />
        ) : tenders.length === 0 ? (
          <EmptyState
            icon={Radar}
            title="No tender opportunities tracked yet"
            subtitle="Structured tender intelligence from Hintco will appear here once collected."
          />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                <th className="pb-2 font-semibold">Opportunity</th>
                <th className="pb-2 font-semibold">Product</th>
                <th className="pb-2 font-semibold">Country</th>
                <th className="pb-2 text-right font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {tenders.slice(0, 8).map((item) => (
                <tr
                  key={item.intelligence_id}
                  className="border-t border-border/60 [&>td]:py-2.5"
                >
                  <td className="max-w-[220px] truncate font-medium text-text-primary">
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="hover:text-aqua"
                    >
                      {item.title}
                    </a>
                  </td>
                  <td className="text-text-secondary">
                    {item.products[0] ?? '—'}
                  </td>
                  <td className="text-text-secondary">
                    {item.countries[0] ?? item.tender_region ?? '—'}
                  </td>
                  <td className="text-right">
                    <StatusChip tone={statusToTone(item.tender_status)}>
                      {item.tender_status ?? 'Tracked'}
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
