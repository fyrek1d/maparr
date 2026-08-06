import { useEffect } from 'react'
import { useAuth } from '@/store'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Map,
  LayoutDashboard,
  Download,
  Layers,
  Users,
  Settings,
  Database,
  LogOut,
  Sun,
  Moon,
} from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/admin/maps', icon: Map, label: 'Maps' },
  { to: '/admin/downloads', icon: Download, label: 'Downloads' },
  { to: '/admin/library', icon: Layers, label: 'Library' },
  { to: '/admin/users', icon: Users, label: 'Users' },
  { to: '/admin/settings', icon: Settings, label: 'Settings' },
  { to: '/admin/storage', icon: Database, label: 'Storage' },
] as const

export default function Layout() {
  const { user, logout, darkMode, toggleDarkMode } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth')
  }

  return (
    <div className="flex min-h-screen w-full">
      <aside className="flex h-screen w-60 flex-shrink-0 flex-col border-r border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
        <div className="flex h-16 items-center gap-2 px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white">
            <Map size={20} />
          </div>
          <span className="text-lg font-bold text-gray-900 dark:text-white">Maparr</span>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
{navItems.map((item) => {
            const active =
              item.to === '/admin'
                ? location.pathname === '/admin'
                : location.pathname.startsWith(item.to)
            return (
              <Link
                key={item.to}
                to={item.to}
                className={clsx(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  active
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800',
                )}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            )
          })}
        </nav>
        <div className="border-t border-gray-200 p-3 dark:border-gray-700">
          <div className="flex items-center gap-3 rounded-md px-3 py-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200">
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">{user?.username}</p>
              <p className="truncate text-xs text-gray-500 dark:text-gray-400">{user?.role}</p>
            </div>
            <button
              onClick={toggleDarkMode}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              title="Toggle dark mode"
            >
              {darkMode ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button onClick={handleLogout} className="text-gray-400 hover:text-red-600" title="Logout">
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto bg-gray-50 p-6 dark:bg-gray-950">
        <Outlet />
      </main>
    </div>
  )
}