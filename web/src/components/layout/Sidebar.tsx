import {
  Brain,
  Building2,
  ChartNoAxesCombined,
  Database,
  FileText,
  Landmark,
  LayoutDashboard,
  Radar,
  Settings,
  Sparkles,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '../../lib/utils'

interface NavItem {
  label: string
  icon: typeof LayoutDashboard
  path?: string
  disabled?: boolean
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const groups: NavGroup[] = [
  {
    label: 'Intelligence',
    items: [
      { label: 'Dashboard', icon: LayoutDashboard, path: '/' },
      { label: 'Intelligence Feed', icon: Brain, disabled: true },
      { label: 'Opportunities', icon: Radar, disabled: true },
    ],
  },
  {
    label: 'Market',
    items: [
      { label: 'Projects', icon: Building2, path: '/projects' },
      { label: 'Companies', icon: Building2, path: '/companies' },
      { label: 'Markets', icon: ChartNoAxesCombined, disabled: true },
      { label: 'Policy', icon: Landmark, disabled: true },
    ],
  },
  {
    label: 'System',
    items: [
      { label: 'Sources', icon: Database, path: '/sources' },
      { label: 'Reports', icon: FileText, disabled: true },
      { label: 'Settings', icon: Settings, disabled: true },
    ],
  },
]

const itemClasses =
  'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors border-l-2'

export function Sidebar() {
  return (
    <aside className="flex h-full w-[240px] shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green/15">
          <span className="text-sm font-bold text-green">G</span>
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight text-text-primary">
            GMIP
          </p>
          <p className="text-[10px] leading-tight text-text-muted">
            Green Molecules Intelligence
          </p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {groups.map((group) => (
          <div key={group.label} className="mb-5">
            <p className="mb-1.5 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-text-disabled">
              {group.label}
            </p>
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) =>
                item.path ? (
                  <NavLink
                    key={item.label}
                    to={item.path}
                    end={item.path === '/'}
                    className={({ isActive }) =>
                      cn(
                        itemClasses,
                        isActive
                          ? 'border-green bg-green/10 text-text-primary'
                          : 'border-transparent text-text-muted hover:bg-surface-elevated hover:text-text-secondary',
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <item.icon
                          className={cn('h-4 w-4', isActive && 'text-green')}
                          strokeWidth={1.75}
                        />
                        {item.label}
                      </>
                    )}
                  </NavLink>
                ) : (
                  <button
                    key={item.label}
                    disabled={item.disabled}
                    title={item.disabled ? 'Coming soon' : undefined}
                    className={cn(
                      itemClasses,
                      'border-transparent text-text-muted',
                      item.disabled &&
                        'cursor-not-allowed opacity-40 hover:bg-transparent',
                    )}
                  >
                    <item.icon className="h-4 w-4" strokeWidth={1.75} />
                    {item.label}
                  </button>
                ),
              )}
            </div>
          </div>
        ))}

        <button
          disabled
          title="Coming soon"
          className="flex w-full cursor-not-allowed items-center gap-2.5 rounded-lg border border-aqua/20 bg-aqua/5 px-2.5 py-2 text-[13px] font-medium text-aqua opacity-60"
        >
          <Sparkles className="h-4 w-4" strokeWidth={1.75} />
          Ask GMIP
        </button>
      </nav>
    </aside>
  )
}
