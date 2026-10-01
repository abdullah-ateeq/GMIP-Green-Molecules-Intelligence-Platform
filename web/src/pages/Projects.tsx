import { Factory } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import { Card, CardContent } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'

export function Projects() {
  const [query, setQuery] = useState('')
  const { data, loading } = useFetch(() => api.projects(500), [])

  const filtered = (data ?? []).filter((project) => {
    if (!query.trim()) return true
    const lowered = query.toLowerCase()
    return (
      project.canonical_name.toLowerCase().includes(lowered) ||
      project.aliases.some((alias) => alias.toLowerCase().includes(lowered))
    )
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold text-text-primary">Projects</h1>
        <p className="mt-1 text-sm text-text-muted">
          Canonical projects resolved from collected intelligence
        </p>
      </div>

      <input
        type="text"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search by project name or alias..."
        className="w-full max-w-md rounded-lg border border-border bg-surface-2 px-3 py-2 text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none"
      />

      <Card>
        <CardContent className="pt-5">
          {loading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={Factory}
              title="No projects tracked yet"
              subtitle="No parser currently extracts named projects from collected intelligence — this page will populate once that coverage exists."
            />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                  <th className="pb-2 font-semibold">Project</th>
                  <th className="pb-2 font-semibold">Country</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((project) => (
                  <tr
                    key={project.entity_id}
                    className="border-t border-border/60 [&>td]:py-2.5"
                  >
                    <td className="font-medium text-text-primary">
                      <Link
                        to={`/projects/${project.entity_id}`}
                        className="hover:text-aqua"
                      >
                        {project.canonical_name}
                      </Link>
                    </td>
                    <td className="text-text-secondary">{project.country ?? '—'}</td>
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
