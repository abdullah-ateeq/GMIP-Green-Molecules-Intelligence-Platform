import { CalendarClock, FileSearch, Radar as RadarIcon, TrendingUp } from 'lucide-react'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import { timeAgo } from '../lib/utils'
import { ActivityChart } from '../components/dashboard/ActivityChart'
import { KpiCard } from '../components/dashboard/KpiCard'
import { LatestIntelligenceFeed } from '../components/dashboard/LatestIntelligenceFeed'
import { MarketSignalsPanel } from '../components/dashboard/MarketSignalsPanel'
import { OfftakeTracker } from '../components/dashboard/OfftakeTracker'
import { OpportunityRadar } from '../components/dashboard/OpportunityRadar'
import { SourceTypeDistribution } from '../components/dashboard/SourceTypeDistribution'
import { TopCountriesTable } from '../components/dashboard/TopCountriesTable'
import { WorldMapCard } from '../components/dashboard/WorldMapCard'

export function Dashboard() {
  const summary = useFetch(() => api.dashboardSummary(), [])
  const intelCount = useFetch(() => api.intelligenceCount(), [])
  const intelCountWeek = useFetch(() => api.intelligenceCount(7), [])
  const tenders = useFetch(() => api.tenderCounts(), [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold text-text-primary">
          Executive Dashboard
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          Global Green Molecules Market Intelligence
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="New Intelligence"
          value={intelCount.data?.total ?? 0}
          subtext={`+${intelCountWeek.data?.total ?? 0} this week`}
          icon={FileSearch}
          accent="aqua"
          loading={intelCount.loading}
        />
        <KpiCard
          label="Open Opportunities"
          value={summary.data?.opportunities ?? 0}
          subtext="Relevant monitored sources"
          icon={RadarIcon}
          accent="green"
          loading={summary.loading}
        />
        <KpiCard
          label="Tracked Tenders"
          value={tenders.data?.total ?? 0}
          subtext={`${tenders.data?.open ?? 0} open · ${tenders.data?.closed ?? 0} closed`}
          icon={TrendingUp}
          accent="emerald"
          loading={tenders.loading}
        />
        <KpiCard
          label="Last Market Scan"
          value={
            summary.data?.last_scan ? timeAgo(summary.data.last_scan) : '—'
          }
          subtext={summary.data?.run_status ?? 'No run yet'}
          icon={CalendarClock}
          accent="lime"
          loading={summary.loading}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ActivityChart />
        </div>
        <SourceTypeDistribution />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-5">
          <WorldMapCard />
          <TopCountriesTable />
          <OpportunityRadar />
          <OfftakeTracker />
        </div>
        <div className="space-y-5">
          <LatestIntelligenceFeed />
          <MarketSignalsPanel />
        </div>
      </div>
    </div>
  )
}
