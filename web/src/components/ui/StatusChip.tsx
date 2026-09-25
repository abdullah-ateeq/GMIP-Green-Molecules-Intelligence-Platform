import { cn } from '../../lib/utils'

export type ChipTone = 'positive' | 'info' | 'watch' | 'risk' | 'neutral'

const toneClasses: Record<ChipTone, string> = {
  positive: 'bg-green/10 text-green border-green/25',
  info: 'bg-aqua/10 text-aqua border-aqua/25',
  watch: 'bg-watch/10 text-watch border-watch/25',
  risk: 'bg-risk/10 text-risk border-risk/25',
  neutral: 'bg-text-muted/10 text-text-muted border-text-muted/25',
}

export function StatusChip({
  tone,
  children,
}: {
  tone: ChipTone
  children: React.ReactNode
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide',
        toneClasses[tone],
      )}
    >
      {children}
    </span>
  )
}

/** Maps the domain-specific statuses used across GMIP to a chip tone. */
export function statusToTone(status: string | null | undefined): ChipTone {
  if (!status) return 'neutral'

  const normalized = status.toLowerCase()

  if (
    ['success', 'active', 'completed', 'open', 'healthy'].includes(
      normalized,
    )
  ) {
    return 'positive'
  }

  if (
    ['pending_credentials', 'pending_license', 'inactive', 'closed'].includes(
      normalized,
    )
  ) {
    return 'neutral'
  }

  if (['completed_with_errors', 'watch'].includes(normalized)) {
    return 'watch'
  }

  if (['failed', 'error', 'permanent_failure'].includes(normalized)) {
    return 'risk'
  }

  return 'neutral'
}
