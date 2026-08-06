import { create } from 'zustand'
import { api, getTokens, setTokens, subscribe } from './lib/api'
import type { User } from './lib/types'

interface AuthState {
  user: User | null
  loading: boolean
  initialized: boolean
  darkMode: boolean
  setUser: (u: User | null) => void
  init: () => Promise<void>
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  toggleDarkMode: () => void
}

const prefersDark = () => {
  try {
    return localStorage.getItem('maparr.dark') === '1'
  } catch {
    return false
  }
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  initialized: false,
  darkMode: prefersDark(),

  init: async () => {
    if (!getTokens()?.access_token) {
      set({ initialized: true })
      return
    }
    try {
      const me = await api.get<User>('/auth/me')
      set({ user: me, initialized: true })
    } catch {
      setTokens(null)
      set({ user: null, initialized: true })
    }
  },

  login: async (username, password) => {
    set({ loading: true })
    try {
      const res = await api.post<{ access_token: string; refresh_token: string }>(
        '/auth/login',
        { username, password },
      )
      setTokens({ access_token: res.access_token, refresh_token: res.refresh_token })
      const me = await api.get<User>('/auth/me')
      set({ user: me, loading: false, initialized: true })
    } catch (e) {
      set({ loading: false })
      throw e
    }
  },

  logout: async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      /* ignore */
    }
    setTokens(null)
    set({ user: null })
  },

  toggleDarkMode: () => {
    const next = !get().darkMode
    try {
      localStorage.setItem('maparr.dark', next ? '1' : '0')
    } catch {
      /* ignore */
    }
    document.documentElement.classList.toggle('dark', next)
    set({ darkMode: next })
  },

  setUser: (u) => set({ user: u }),
}))

// Clear session on external token removal (e.g. expired refresh).
subscribe(() => {
  if (!getTokens()?.access_token) {
    useAuth.getState().setUser(null)
  }
})