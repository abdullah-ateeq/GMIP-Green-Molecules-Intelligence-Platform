import { ExternalLink } from 'lucide-react'
import { cn } from '../../lib/utils'

/**
 * Shared "View Original Source" action — one place that decides whether
 * a source_url is safe to open, so every card (Latest Intelligence,
 * Opportunity Radar, Offtake Tracker) behaves consistently.
 *
 * `available` is boolean|null: null means the link has never been
 * checked (the honest default — most links haven't been verified yet),
 * and is treated the same as "available" so an unverified link still
 * opens normally. Only an explicit `false` (a real HTTP 404/410 check)
 * blocks the click and shows the unavailable state instead.
 */
export function SourceLink({
  url,
  available,
  className,
}: {
  url: string
  available: boolean | null
  className?: string
}) {
  if (available === false) {
    return (
      <span
        className={cn('inline-flex items-center gap-1 text-xs text-text-muted', className)}
        title="This source was checked and no longer resolves (404/410)."
      >
        Original source currently unavailable
      </span>
    )
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(event) => event.stopPropagation()}
      className={cn(
        'inline-flex items-center gap-1 text-xs text-aqua hover:underline',
        className,
      )}
    >
      View Original Source
      <ExternalLink className="h-3 w-3" strokeWidth={1.75} />
    </a>
  )
}
