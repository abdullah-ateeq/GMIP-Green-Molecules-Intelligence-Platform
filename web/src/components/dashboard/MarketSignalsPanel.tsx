import { Sparkles } from 'lucide-react'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'

export function MarketSignalsPanel() {
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Market Signals</CardTitle>
          <CardSubtitle>Cross-source pattern detection</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon={Sparkles}
          title="Signal engine not yet built"
          subtitle="Market signals (demand shifts, investment momentum, emerging corridors) require the Signal Engine phase — combining events across sources once entity resolution is in place. Not fabricated here ahead of that."
        />
      </CardContent>
    </Card>
  )
}
