import { Activity } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../../lib/api'
import { useFetch } from '../../lib/useFetch'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { Skeleton } from '../ui/Skeleton'

const SERIES: { key: 'projects' | 'tenders' | 'offtake' | 'fid' | 'policy'; name: string; color: string }[] = [
  { key: 'projects', name: 'Projects', color: '#2AD4C9' },
  { key: 'tenders', name: 'Tenders', color: '#24D17E' },
  { key: 'offtake', name: 'Offtake', color: '#A3E635' },
  { key: 'fid', name: 'FID', color: '#12B76A' },
  { key: 'policy', name: 'Policy', color: '#F7B84B' },
]

export function ActivityChart() {
  const { data, loading } = useFetch(() => api.businessActivity(30), [])

  const hasAnyActivity = (data ?? []).some((point) =>
    SERIES.some((series) => point[series.key] > 0),
  )

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Project &amp; Opportunity Activity</CardTitle>
          <CardSubtitle>Real business events, last 30 days</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-64 w-full" />
        ) : !data || data.length === 0 || !hasAnyActivity ? (
          <EmptyState
            icon={Activity}
            title="No business events detected yet"
            subtitle="Project, tender, offtake, FID and policy events will appear here as parsers extract them from collected intelligence."
          />
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#253129"
                vertical={false}
              />
              <XAxis
                dataKey="day"
                tick={{ fill: '#8B9A90', fontSize: 11 }}
                axisLine={{ stroke: '#253129' }}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: '#8B9A90', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={28}
              />
              <Tooltip
                contentStyle={{
                  background: '#1A241E',
                  border: '1px solid #253129',
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: '#F4F7F5' }}
                cursor={{ fill: '#1A241E' }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: '#8B9A90' }}
                iconType="circle"
                iconSize={8}
              />
              {SERIES.map((series) => (
                <Bar
                  key={series.key}
                  dataKey={series.key}
                  name={series.name}
                  fill={series.color}
                  radius={[3, 3, 0, 0]}
                  maxBarSize={24}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
