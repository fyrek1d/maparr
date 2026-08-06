import { useQuery } from '@tanstack/react-query'
import { Map as MapIcon, Layers, Download, Database, Activity } from 'lucide-react'
import { Link } from 'react-router-dom'

import { PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import { formatBytes } from '@/lib/utils'
import type { MapItem, SystemStats } from '@/lib/types'

export default function AdminDashboard() {
  const stats = useQuery({ queryKey: ['system'], queryFn: () => api.get<SystemStats>('/settings/system') })
  const maps = useQuery({
    queryKey: ['maps'],
    queryFn: () => api.get<MapItem[]>('/maps'),
  })

  const events = ['download.completed', 'download.failed', 'backup.created']

  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard" description="Maparr system overview." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatLink icon={<MapIcon size={28} />} label="Maps" value={String(stats.data?.maps_count ?? 0)} to="/admin/library" />
        <StatLink icon={<Layers size={28} />} label="Providers" value={String((maps.data ?? []).length > 0 ? 'ready' : 'available')} />
        <StatLink icon={<Download size={28} />} label="Active downloads" value={String(stats.data?.active_downloads ?? 0)} to="/admin/downloads" />
        <StatLink icon={<Database size={28} />} label="Storage" value={formatBytes(stats.data?.total_bytes ?? 0)} to="/admin/storage" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-2 text-lg font-semibold">Recent maps</h2>
          <div className="space-y-2">
            {(maps.data ?? []).slice(0, 6).map((m) => (
              <div key={m.id} className="flex items-center justify-between rounded border border-gray-200 px-3 py-2 text-sm">
                <span className="truncate font-medium">{m.name}</span>
                <span className="ml-2 shrink-0 text-xs text-gray-400">{m.status} · {formatBytes(m.file_size || m.bytes_done)}</span>
              </div>
            ))}
            {!maps.data?.length && <p className="text-sm text-gray-400">No maps yet.</p>}
          </div>
        </div>

        <div>
          <h2 className="mb-2 text-lg font-semibold">System</h2>
          <div className="rounded border border-gray-200 p-4 text-sm">
            <Row label="Disk free" value={formatBytes(stats.data?.disk_free_bytes ?? 0)} />
            <Row label="Database size" value={formatBytes(stats.data?.db_size_bytes ?? 0)} />
            <Row label="Tiles served" value={(stats.data?.tiles_served ?? 0).toLocaleString()} />
          </div>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-gray-100 py-2 last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

function StatLink({ icon, label, value, to }: { icon: React.ReactNode; label: string; value: string; to?: string }) {
  const inner = (
    <div className="flex items-center gap-4 px-5 py-4">
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-900/40">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm text-gray-500">{label}</p>
        <p className="truncate text-2xl font-bold">{value}</p>
      </div>
    </div>
  )
  return to ? (
    <Link to={to} className="card transition-shadow hover:shadow-md">{inner}</Link>
  ) : (
    <div className="card">{inner}</div>
  )
}