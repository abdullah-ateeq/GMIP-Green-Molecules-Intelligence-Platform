import { Building2, Factory, Newspaper, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type EntitySummary, type IntelligenceSearchResult } from '../../lib/api'

const MIN_QUERY_LENGTH = 2
const DEBOUNCE_MS = 250

export function GlobalSearch() {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [companies, setCompanies] = useState<EntitySummary[]>([])
  const [projects, setProjects] = useState<EntitySummary[]>([])
  const [intelligence, setIntelligence] = useState<IntelligenceSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const trimmed = query.trim()

    if (trimmed.length < MIN_QUERY_LENGTH) {
      setCompanies([])
      setProjects([])
      setIntelligence([])
      setLoading(false)
      return
    }

    setLoading(true)
    const timeout = setTimeout(() => {
      Promise.all([
        api.searchEntities(trimmed, 'COMPANY'),
        api.searchEntities(trimmed, 'PROJECT'),
        api.searchIntelligence(trimmed, 5),
      ])
        .then(([companyResults, projectResults, intelligenceResults]) => {
          setCompanies(companyResults)
          setProjects(projectResults)
          setIntelligence(intelligenceResults)
        })
        .catch(() => {
          setCompanies([])
          setProjects([])
          setIntelligence([])
        })
        .finally(() => setLoading(false))
    }, DEBOUNCE_MS)

    return () => clearTimeout(timeout)
  }, [query])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const trimmed = query.trim()
  const hasResults = companies.length > 0 || projects.length > 0 || intelligence.length > 0
  const showDropdown = open && trimmed.length >= MIN_QUERY_LENGTH

  function goToEntity(entity: EntitySummary) {
    setOpen(false)
    setQuery('')
    navigate(
      entity.entity_type === 'COMPANY'
        ? `/companies/${entity.entity_id}`
        : `/projects/${entity.entity_id}`,
    )
  }

  return (
    <div ref={containerRef} className="relative flex max-w-md flex-1">
      <div className="flex w-full items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2">
        <Search className="h-4 w-4 text-text-muted" strokeWidth={1.75} />
        <input
          type="text"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          placeholder="Search projects, companies, tenders, policies..."
          className="w-full bg-transparent text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none"
        />
      </div>

      {showDropdown && (
        <div className="absolute left-0 top-full z-20 mt-2 max-h-[420px] w-full overflow-y-auto rounded-lg border border-border bg-surface-elevated shadow-lg">
          {loading ? (
            <p className="px-3 py-4 text-center text-xs text-text-muted">Searching…</p>
          ) : !hasResults ? (
            <p className="px-3 py-4 text-center text-xs text-text-muted">
              No matches for "{trimmed}"
            </p>
          ) : (
            <div className="py-1.5">
              {companies.length > 0 && (
                <div className="mb-1">
                  <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-muted">
                    Companies
                  </p>
                  {companies.map((company) => (
                    <button
                      key={company.entity_id}
                      onClick={() => goToEntity(company)}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] text-text-primary hover:bg-surface-2"
                    >
                      <Building2 className="h-3.5 w-3.5 text-aqua" strokeWidth={1.75} />
                      {company.canonical_name}
                      {company.aliases.length > 0 && (
                        <span className="text-xs text-text-muted">
                          (matched via {company.aliases.join(', ')})
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {projects.length > 0 && (
                <div className="mb-1">
                  <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-muted">
                    Projects
                  </p>
                  {projects.map((project) => (
                    <button
                      key={project.entity_id}
                      onClick={() => goToEntity(project)}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] text-text-primary hover:bg-surface-2"
                    >
                      <Factory className="h-3.5 w-3.5 text-green" strokeWidth={1.75} />
                      {project.canonical_name}
                    </button>
                  ))}
                </div>
              )}

              {intelligence.length > 0 && (
                <div>
                  <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-muted">
                    Intelligence
                  </p>
                  {intelligence.map((item) => (
                    <a
                      key={item.intelligence_id}
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start gap-2 px-3 py-2 text-left text-[13px] text-text-primary hover:bg-surface-2"
                    >
                      <Newspaper
                        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-lime"
                        strokeWidth={1.75}
                      />
                      <span className="line-clamp-2">{item.title}</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
