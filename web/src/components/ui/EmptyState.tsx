import type { LucideIcon } from 'lucide-react'

export function EmptyState({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: LucideIcon
  title: string
  subtitle: string
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <Icon className="h-7 w-7 text-text-disabled" strokeWidth={1.5} />
      <p className="text-sm font-medium text-text-secondary">{title}</p>
      <p className="max-w-xs text-xs text-text-muted">{subtitle}</p>
    </div>
  )
}
