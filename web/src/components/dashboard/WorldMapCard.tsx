import { Globe2 } from 'lucide-react'
import { useState } from 'react'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { api } from '../../lib/api'
import { useFetch } from '../../lib/useFetch'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { Skeleton } from '../ui/Skeleton'

const GEO_URL =
  'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

// Natural Earth's `name` property doesn't always match our collected
// country strings verbatim — a small alias table covers the mismatches
// for the countries GMIP actually tracks (see hydrogen_council_parser.py).
const NAME_ALIASES: Record<string, string> = {
  'united states': 'united states of america',
  'south korea': 'south korea',
  'korea, rep.': 'south korea',
}

function normalize(name: string): string {
  const lower = name.toLowerCase()
  return NAME_ALIASES[lower] ?? lower
}

export function WorldMapCard() {
  const { data, loading } = useFetch(() => api.countryMentions(50), [])
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const mentionsByCountry = new Map(
    (data ?? []).map((row) => [normalize(row.country), row.mentions]),
  )
  const maxMentions = Math.max(1, ...(data ?? []).map((row) => row.mentions))

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Global Hydrogen &amp; Ammonia Activity</CardTitle>
          <CardSubtitle>
            Countries mentioned across collected intelligence
          </CardSubtitle>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-72 w-full" />
        ) : !data || data.length === 0 ? (
          <EmptyState
            icon={Globe2}
            title="No geographic activity yet"
            subtitle="Countries will highlight here as intelligence objects are collected."
          />
        ) : (
          <div className="overflow-hidden rounded-xl bg-surface-2">
            <ComposableMap
              projectionConfig={{ scale: 170 }}
              style={{ width: '100%', height: '360px' }}
            >
              <Geographies geography={GEO_URL}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const name: string = geo.properties?.name ?? ''
                    const mentions = mentionsByCountry.get(normalize(name)) ?? 0
                    const intensity = mentions / maxMentions
                    const isHovered = hoveredId === geo.rsmKey

                    const baseFill =
                      mentions > 0
                        ? `rgba(36, 209, 126, ${0.2 + intensity * 0.7})`
                        : 'var(--color-surface-elevated)'

                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill={
                          isHovered
                            ? mentions > 0
                              ? '#24D17E'
                              : 'var(--color-border)'
                            : baseFill
                        }
                        stroke="var(--color-border)"
                        strokeWidth={0.4}
                        style={{ outline: 'none' }}
                        onMouseEnter={() => setHoveredId(geo.rsmKey)}
                        onMouseLeave={() => setHoveredId(null)}
                      >
                        <title>
                          {name}
                          {mentions > 0 ? ` — ${mentions} mention(s)` : ''}
                        </title>
                      </Geography>
                    )
                  })
                }
              </Geographies>
            </ComposableMap>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
