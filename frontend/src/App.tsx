import { lazy, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './store'
import { LoadingSpinner } from './components/ui'

const Login = lazy(() => import('./pages/Login'))
const Onboarding = lazy(() => import('./pages/Onboarding'))
const Layout = lazy(() => import('./pages/Layout'))
const Admin = lazy(() => import('./pages/Admin'))
const MapPage = lazy(() => import('./pages/Map'))

export default function App() {
  const { init, initialized, user, darkMode, toggleDarkMode } = useAuth()

  useEffect(() => {
    init()
    // Apply dark mode class
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [init, darkMode])

  if (!initialized) {
    return (
      <div className="flex items-center justify-center min-h-screen w-full">
        <LoadingSpinner />
      </div>
    )
  }

  const isAuthed = !!user

  return (
    <Routes>
      {/* Onboarding (visible only if no users exist? but we allow always) */}
      <Route path="/onboarding" element={!isAuthed ? <Onboarding /> : <Navigate to="/" replace />} />

      {/* Auth routes */}
      <Route path="/auth/login" element={!isAuthed ? <Login /> : <Navigate to="/" replace />} />
      <Route path="/auth" element={<Navigate to="/auth/login" replace />} />

      {/* Protected app routes */}
      <Route path="/" element={isAuthed ? <Layout /> : <Navigate to="/auth/login" replace />}>
        <Route index element={<Admin />} />
        <Route path="admin" element={<Admin />} />
        <Route path="map" element={<MapPage />} />
        <Route path="map/:mapId" element={<MapPage />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to={isAuthed ? '/' : '/auth/login'} replace />} />
    </Routes>
  )
}