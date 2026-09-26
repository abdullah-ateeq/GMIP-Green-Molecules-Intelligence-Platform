export type Theme = 'dark' | 'light'

const STORAGE_KEY = 'gmip-theme'

export function getStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme)

  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Per-viewer convenience only — safe to ignore if storage is blocked.
  }
}
