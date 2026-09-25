import type { LucideIcon } from 'lucide-react'
import { cn } from '../../lib/utils'
import { Skeleton } from '../ui/Skeleton'

type Accent = 'aqua' | 'green' | 'emerald' | 'lime'

const accentClasses: Record<Accent, { bar: string; icon: string; bg: string }> = {
  aqua: { bar: 'bg-aqua', icon: 'text-aqua', bg: 'bg-aqua/10' },
  green: { bar: 'bg-green', icon: 'text-green', bg: 'bg-green/10' },
  emerald: { bar: 'bg-emerald', icon: 'text-emerald', bg: 'bg-emerald/10' },
  lime: { bar: 'bg-lime', icon: 'text-lime', bg: 'bg-lime/10' },
}

export function KpiCard({
  label,
  value,
  subtext,
  icon: Icon,
  accent,
  loading,
}: {
  label: string
  value: string | number
  subtext: string
  icon: LucideIcon
  accent: Accent
  loading?: boolean
}) {
  const tone = accentClasses[accent]

  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className={cn('mb-3 h-1 w-8 rounded-full', tone.bar)} />

      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">
            {label}
          </p>
          {loading ? (
            <Skeleton className="mt-2 h-8 w-16" />
          ) : (
            <p className="mt-1 text-[30px] font-semibold leading-none text-text-primary">
              {value}
            </p>
          )}
        </div>
        <div className={cn('rounded-lg p-2', tone.bg)}>
          <Icon className={cn('h-4 w-4', tone.icon)} strokeWidth={1.75} />
        </div>
      </div>

      <p className="mt-3 text-xs text-text-muted">{subtext}</p>
    </div>
  )
}
