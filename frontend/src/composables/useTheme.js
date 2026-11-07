import { ref } from 'vue'

const STORAGE_KEY = 'info-arena-theme'
const theme = ref('system')

function preferredTheme() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(value) {
  theme.value = value
  const root = document.documentElement
  if (value === 'system') root.removeAttribute('data-theme')
  else root.dataset.theme = value
  if (value === 'system') localStorage.removeItem(STORAGE_KEY)
  else localStorage.setItem(STORAGE_KEY, value)
}

function initializeTheme() {
  const saved = localStorage.getItem(STORAGE_KEY)
  applyTheme(saved === 'light' || saved === 'dark' ? saved : 'system')
}

function toggleTheme() {
  const active = theme.value === 'system' ? preferredTheme() : theme.value
  applyTheme(active === 'dark' ? 'light' : 'dark')
}

export function useTheme() {
  return { theme, initializeTheme, toggleTheme }
}
