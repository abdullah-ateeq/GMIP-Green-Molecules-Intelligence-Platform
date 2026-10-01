import { ArrowLeft, Factory } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import { timeAgo } from '../lib/utils'
import { Card, CardContent, CardHeader, CardSubtitle, CardTitle } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'
import { SourceLink } from '../components/ui/SourceLink'

export function ProjectDetail() {
  const { entityId } = useParams<{ entityId: string }>()
  const { data: profile, loading, error } = useFetch(
    () => api.projectDetail(entityId!),
    [entityId],
  )

  if (loading) {
    return <Skeleton className="h-64 w-full" />
  }

  if (error || !profile) {
    return (
      <EmptyState
        icon={Factory}
        title="Project not found"
        subtitle="This canonical project record may have been merged into another."
      />
    )
  }

  const { entity } = profile

  return (
    <div className="space-y-6">
      <Link
        to="/projects"
        className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary"
      >
        <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
        Back to Projects
      </Link>

      <div>
        <h1 className="text-[28px] font-semibold text-text-primary">
          {entity.canonical_name}
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          {entity.country ?? 'Country unknown'}
        </p>
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Latest Intelligence</CardTitle>
            <CardSubtitle>Evidence this canonical project was resolved from</CardSubtitle>
          </div>
        </CardHeader>
        <CardContent>
          {profile.latest_intelligence.length === 0 ? (
            <EmptyState
              icon={Factory}
              title="No intelligence mentions yet"
              subtitle="No supporting intelligence has been linked to this project record."
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
    </div>
  )
}
