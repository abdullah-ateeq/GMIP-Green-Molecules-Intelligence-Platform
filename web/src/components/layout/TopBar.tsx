import { Bell, Download, Moon, RefreshCw, Sun, UserCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import { applyTheme, getStoredTheme, type Theme } from '../../lib/theme'
import { timeAgo } from '../../lib/utils'
import { cn } from '../../lib/utils'
import { useFetch } from '../../lib/useFetch'
import { GlobalSearch } from './GlobalSearch'

export function TopBar() {
  const [theme, setTheme] = useState<Theme>('dark')
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const summary = useFetch(() => api.dashboardSummary(), [])

  useEffect(() => {
    setTheme(getStoredTheme())
  }, [])

  function toggleTheme() {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    applyTheme(next)
  }

  async function handleRefresh() {
    if (refreshing) return

    setRefreshing(true)
    setRefreshError(null)

    try {
      // Triggers a real collection run across every registered source
      // (Hintco, Hydrogen Council, H2 View) — can take a couple of minutes.
      await api.collectRun()
      window.location.reload()
    } catch (error) {
      setRefreshing(false)
      setRefreshError(
        error instanceof Error ? error.message : 'Refresh failed',
      )
    }
  }

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
      <GlobalSearch />

      <div className="flex items-center gap-3">
        <div
          className="hidden items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-[12px] text-text-muted lg:flex"
          title={summary.data?.run_status ?? 'No run yet'}
        >
          <span
            className={cn(
              'h-1.5 w-1.5 rounded-full',
              summary.data?.run_status === 'COMPLETED'
                ? 'bg-green'
                : summary.data?.run_status
                  ? 'bg-amber'
                  : 'bg-text-muted',
            )}
          />
          Last scan:{' '}
          {summary.data?.last_scan ? timeAgo(summary.data.last_scan) : '—'}
        </div>

        <div className="relative">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            title={
              refreshing
                ? 'Refreshing all sources — this can take a couple of minutes...'
                : 'Fetch the latest from Hintco, Hydrogen Council and H2 View'
            }
            className={cn(
              'flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-[13px] font-medium text-text-secondary transition-colors hover:bg-surface-elevated',
              refreshing && 'cursor-not-allowed opacity-70',
            )}
          >
            <RefreshCw
              className={cn('h-3.5 w-3.5', refreshing && 'animate-spin')}
              strokeWidth={1.75}
            />
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>

          {refreshError && (
            <div className="absolute right-0 top-full z-10 mt-2 w-64 rounded-lg border border-risk/25 bg-surface-elevated px-3 py-2 text-xs text-risk shadow-lg">
              {refreshError}
            </div>
          )}
        </div>

        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          className="rounded-lg p-2 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-secondary"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4" strokeWidth={1.75} />
          ) : (
            <Moon className="h-4 w-4" strokeWidth={1.75} />
          )}
        </button>

        <button className="rounded-lg p-2 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-secondary">
          <Bell className="h-4 w-4" strokeWidth={1.75} />
        </button>

        <button className="flex items-center gap-1.5 rounded-lg bg-emerald px-3.5 py-2 text-[13px] font-medium text-white transition-opacity hover:opacity-90">
          <Download className="h-3.5 w-3.5" strokeWidth={2} />
          Export Intelligence
        </button>

        <button className="rounded-lg p-1 text-text-muted transition-colors hover:text-text-secondary">
          <UserCircle className="h-6 w-6" strokeWidth={1.5} />
        </button>
      </div>
    </header>
  )
}
