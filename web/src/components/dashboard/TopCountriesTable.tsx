import { MapPin } from 'lucide-react'
import { api } from '../../lib/api'
import { useFetch } from '../../lib/useFetch'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { Skeleton } from '../ui/Skeleton'

export function TopCountriesTable() {
  const { data, loading } = useFetch(() => api.countryMentions(8), [])

  const maxMentions = Math.max(1, ...(data ?? []).map((row) => row.mentions))

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Top Countries by Activity</CardTitle>
          <CardSubtitle>By intelligence mentions collected</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-48 w-full" />
        ) : !data || data.length === 0 ? (
          <EmptyState
            icon={MapPin}
            title="No country activity yet"
            subtitle="Country rankings populate as intelligence is collected."
          />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                <th className="pb-2 font-semibold">Country</th>
                <th className="pb-2 text-right font-semibold">Mentions</th>
                <th className="pb-2 pl-4 font-semibold">Activity</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr
                  key={row.country}
                  className="border-t border-border/60 [&>td]:py-2.5"
                >
                  <td className="font-medium text-text-primary">
                    {row.country}
                  </td>
                  <td className="text-right text-text-secondary">
                    {row.mentions}
                  </td>
                  <td className="pl-4">
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-surface-2">
                      <div
                        className="h-full rounded-full bg-aqua"
                        style={{
                          width: `${(row.mentions / maxMentions) * 100}%`,
                        }}
                      />
                    </div>
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
