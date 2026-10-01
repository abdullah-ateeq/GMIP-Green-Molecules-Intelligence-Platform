import { ArrowLeft, Building2 } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import { timeAgo } from '../lib/utils'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'
import { SourceLink } from '../components/ui/SourceLink'

export function CompanyDetail() {
  const { entityId } = useParams<{ entityId: string }>()
  const { data: profile, loading, error } = useFetch(
    () => api.companyDetail(entityId!),
    [entityId],
  )

  if (loading) {
    return <Skeleton className="h-64 w-full" />
  }

  if (error || !profile) {
    return (
      <EmptyState
        icon={Building2}
        title="Company not found"
        subtitle="This canonical company record may have been merged into another."
      />
    )
  }

  const { entity } = profile

  return (
    <div className="space-y-6">
      <Link
        to="/companies"
        className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary"
      >
        <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
        Back to Companies
      </Link>

      <div>
        <h1 className="text-[28px] font-semibold text-text-primary">
          {entity.canonical_name}
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          {entity.country ?? 'Country unknown'}
          {entity.aliases.length > 0 && ` · Also known as: ${entity.aliases.join(', ')}`}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">
              Intelligence Mentions
            </p>
            <p className="mt-1 text-[26px] font-semibold text-text-primary">
              {profile.mention_count}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">
              Countries
            </p>
            <p className="mt-1 text-[26px] font-semibold text-text-primary">
              {profile.countries.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">
              Products
            </p>
            <p className="mt-1 text-[26px] font-semibold text-text-primary">
              {profile.products.length}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Latest Intelligence</CardTitle>
            <CardSubtitle>Evidence this canonical company was resolved from</CardSubtitle>
          </div>
        </CardHeader>
        <CardContent>
          {profile.latest_intelligence.length === 0 ? (
            <EmptyState
              icon={Building2}
              title="No intelligence mentions yet"
              subtitle="This company exists in the seed list but hasn't been mentioned in collected intelligence yet."
            />
          ) : (
            <div className="space-y-3">
              {profile.latest_intelligence.map((mention) => (
                <div
                  key={mention.intelligence_object_id}
                  className="rounded-lg border border-border/60 px-3 py-3"
                >
                  <p className="text-[13px] font-medium text-text-primary">
                    {mention.title}
                  </p>
                  <p className="mt-1 text-xs text-text-muted">
                    Mentioned as "{mention.original_mention}" · {timeAgo(mention.collected_at)}
                  </p>
                  <div className="mt-2">
                    <SourceLink url={mention.source_url} available={null} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {profile.relationships.length > 0 && (
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Relationships</CardTitle>
              <CardSubtitle>Only relationships with direct supporting evidence</CardSubtitle>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-text-secondary">
              {profile.relationships.map((rel) => (
                <li key={rel.relationship_id}>
                  {rel.relationship_type} · confidence {Math.round(rel.confidence * 100)}%
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
