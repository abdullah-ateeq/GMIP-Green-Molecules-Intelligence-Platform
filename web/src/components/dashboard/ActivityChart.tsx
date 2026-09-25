import { Activity } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
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

export function ActivityChart() {
  const { data, loading } = useFetch(() => api.activity(30), [])

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Project &amp; Opportunity Activity</CardTitle>
          <CardSubtitle>Intelligence objects collected, last 30 days</CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-64 w-full" />
        ) : !data || data.length === 0 ? (
          <EmptyState
            icon={Activity}
            title="No activity yet"
            subtitle="Collected intelligence will appear here once sources are scanned."
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
              <Bar
                dataKey="total"
                name="Intelligence items"
                fill="#2AD4C9"
                radius={[4, 4, 0, 0]}
                maxBarSize={56}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
