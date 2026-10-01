import { Building2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import { Card, CardContent } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'

export function Companies() {
  const [query, setQuery] = useState('')
  const { data, loading } = useFetch(() => api.companies(500), [])

  const filtered = (data ?? []).filter((company) => {
    if (!query.trim()) return true
    const lowered = query.toLowerCase()
    return (
      company.canonical_name.toLowerCase().includes(lowered) ||
      company.aliases.some((alias) => alias.toLowerCase().includes(lowered))
    )
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold text-text-primary">Companies</h1>
        <p className="mt-1 text-sm text-text-muted">
          Canonical companies resolved from collected intelligence
        </p>
      </div>

      <input
        type="text"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search by name or alias..."
        className="w-full max-w-md rounded-lg border border-border bg-surface-2 px-3 py-2 text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none"
      />

      <Card>
        <CardContent className="pt-5">
          {loading ? (
            <div className="space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={Building2}
              title="No companies found"
              subtitle={
                query
                  ? 'No canonical company matches that search.'
                  : 'Companies are created as entity resolution runs over collected intelligence.'
              }
            />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                  <th className="pb-2 font-semibold">Company</th>
                  <th className="pb-2 font-semibold">Aliases</th>
                  <th className="pb-2 font-semibold">Country</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((company) => (
                  <tr
                    key={company.entity_id}
                    className="border-t border-border/60 [&>td]:py-2.5"
                  >
                    <td className="font-medium text-text-primary">
                      <Link
                        to={`/companies/${company.entity_id}`}
                        className="hover:text-aqua"
                      >
                        {company.canonical_name}
                      </Link>
                    </td>
                    <td className="text-text-secondary">
                      {company.aliases.length > 0 ? company.aliases.join(', ') : '—'}
                    </td>
                    <td className="text-text-secondary">{company.country ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
