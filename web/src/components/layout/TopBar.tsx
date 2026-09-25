import { Bell, Download, Search, UserCircle } from 'lucide-react'

export function TopBar() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
      <div className="flex max-w-md flex-1 items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2">
        <Search className="h-4 w-4 text-text-muted" strokeWidth={1.75} />
        <input
          type="text"
          placeholder="Search projects, companies, tenders, policies..."
          className="w-full bg-transparent text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none"
        />
      </div>

      <div className="flex items-center gap-3">
        <button className="rounded-lg p-2 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-secondary">
          <Bell className="h-4 w-4" strokeWidth={1.75} />
        </button>

        <button className="flex items-center gap-1.5 rounded-lg bg-emerald px-3.5 py-2 text-[13px] font-medium text-background transition-opacity hover:opacity-90">
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
