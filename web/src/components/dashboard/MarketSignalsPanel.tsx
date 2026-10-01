import { Sparkles } from 'lucide-react'
import { api } from '../../lib/api'
import { useFetch } from '../../lib/useFetch'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { Skeleton } from '../ui/Skeleton'

export function MarketSignalsPanel() {
  const { data, loading } = useFetch(() => api.businessSignals(), [])

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Market Signals</CardTitle>
          <CardSubtitle>Cross-source pattern detection (deterministic, first version)</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-40 w-full" />
        ) : !data || data.length === 0 ? (
          <EmptyState
            icon={Sparkles}
            title="No signals detected yet"
            subtitle="A signal appears once at least 3 related events (tender, offtake, project, or policy) are collected for the same country within 30 days."
          />
        ) : (
          <div className="space-y-3">
            {data.map((signal, index) => (
              <div
                key={`${signal.signal_type}-${signal.region}-${index}`}
                className="rounded-lg border border-border/60 bg-surface-2 p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-aqua">
                    {signal.signal_type}
                  </span>
                  <span className="text-[11px] text-text-muted">
                    {signal.confidence}% confidence
                  </span>
                </div>
                <p className="mt-1.5 text-sm text-text-primary">{signal.message}</p>
                <p className="mt-1 text-xs text-text-muted">
                  {signal.supporting_event_count} supporting event
                  {signal.supporting_event_count === 1 ? '' : 's'}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
