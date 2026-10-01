import { FileSearch, Flag, Handshake, Radar as RadarIcon } from 'lucide-react'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
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
  const kpis = useFetch(() => api.businessKpis(), [])

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
          value={kpis.data?.new_intelligence_total ?? 0}
          subtext={`+${kpis.data?.new_intelligence_7d ?? 0} this week`}
          icon={FileSearch}
          accent="aqua"
          loading={kpis.loading}
        />
        <KpiCard
          label="Open Opportunities"
          value={kpis.data?.open_opportunities ?? 0}
          subtext={`${kpis.data?.closed_opportunities ?? 0} closed`}
          icon={RadarIcon}
          accent="green"
          loading={kpis.loading}
        />
        <KpiCard
          label="Projects Reaching FID"
          value={kpis.data?.fid_count_30d ?? 0}
          subtext={
            kpis.data?.fid_count_30d
              ? 'Last 30 days'
              : 'No FID events detected'
          }
          icon={Flag}
          accent="emerald"
          loading={kpis.loading}
        />
        <KpiCard
          label="New Offtake Agreements"
          value={kpis.data?.offtake_count_30d ?? 0}
          subtext={
            kpis.data?.offtake_count_30d
              ? `${kpis.data?.offtake_total ?? 0} tracked total`
              : 'No offtake events detected'
          }
          icon={Handshake}
          accent="lime"
          loading={kpis.loading}
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
