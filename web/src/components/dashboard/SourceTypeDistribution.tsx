import { PieChart } from 'lucide-react'
import { api } from '../../lib/api'
import { useFetch } from '../../lib/useFetch'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { Skeleton } from '../ui/Skeleton'

const BAR_COLORS = ['#24D17E', '#2AD4C9', '#A3E635', '#F7B84B', '#12B76A']

const CATEGORY_LABELS: Record<string, string> = {
  official_procurement: 'Procurement',
  industry_body: 'Industry Body',
  industry_media: 'Media / Discovery',
  premium_market_data: 'Premium Data',
  uncategorised: 'Uncategorised',
}

export function SourceTypeDistribution() {
  const { data, loading } = useFetch(() => api.businessSourceCategories(), [])

  const total = data?.reduce((sum, row) => sum + row.total, 0) ?? 0

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Intelligence by Source Type</CardTitle>
          <CardSubtitle>Collected intelligence, by source category</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-6 w-full" />
            ))}
          </div>
        ) : !data || data.length === 0 ? (
          <EmptyState
            icon={PieChart}
            title="No intelligence collected yet"
            subtitle="Source distribution appears once collection runs produce intelligence objects."
          />
        ) : (
          <div className="space-y-3.5">
            {data.map((row, index) => {
              const pct = total > 0 ? Math.round((row.total / total) * 100) : 0
              return (
                <div key={row.source_category}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-medium text-text-secondary">
                      {CATEGORY_LABELS[row.source_category] ?? row.source_category}
                    </span>
                    <span className="text-text-muted">
                      {pct}% &middot; {row.total}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: BAR_COLORS[index % BAR_COLORS.length],
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
