import { Handshake } from 'lucide-react'
import { api } from '../../lib/api'
import { useFetch } from '../../lib/useFetch'
import { timeAgo } from '../../lib/utils'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { Skeleton } from '../ui/Skeleton'

export function OfftakeTracker() {
  const { data, loading } = useFetch(() => api.recentIntelligence(50), [])
  const offtakes = (data ?? []).filter((item) => item.intelligence_type === 'offtake')

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Offtake Agreement Tracker</CardTitle>
          <CardSubtitle>Signed supply and offtake deals detected across sources</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-40 w-full" />
        ) : offtakes.length === 0 ? (
          <EmptyState
            icon={Handshake}
            title="No offtake agreements detected yet"
            subtitle="Signed supply/offtake deals mentioned by Hintco, Hydrogen Council, or H2 View will appear here."
          />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                <th className="pb-2 font-semibold">Agreement</th>
                <th className="pb-2 font-semibold">Companies</th>
                <th className="pb-2 font-semibold">Product</th>
                <th className="pb-2 font-semibold">Volume</th>
                <th className="pb-2 font-semibold">Duration</th>
                <th className="pb-2 text-right font-semibold">Detected</th>
              </tr>
            </thead>
            <tbody>
              {offtakes.slice(0, 8).map((item) => (
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
                  <td className="max-w-[180px] truncate text-text-secondary">
                    {item.companies.length > 0 ? item.companies.join(', ') : '—'}
                  </td>
                  <td className="text-text-secondary">
                    {item.offtake_product ?? item.products[0] ?? '—'}
                  </td>
                  <td className="text-text-secondary">{item.offtake_volume ?? '—'}</td>
                  <td className="text-text-secondary">{item.offtake_duration ?? '—'}</td>
                  <td className="text-right text-text-muted">
                    {timeAgo(item.collected_at)}
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
