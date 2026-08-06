import { useQuery } from '@tanstack/react-query'
import { Database, HardDrive } from 'lucide-react'

import { Card, PageHeader, ProgressBar } from '@/components/ui'
import { api } from '@/lib/api'
import { formatBytes } from '@/lib/utils'
import type { StorageBreakdown, SystemStats } from '@/lib/types'

export default function Storage() {
  const storage = useQuery({ queryKey: ['storage'], queryFn: () => api.get<StorageBreakdown>('/maps/storage') })
  const stats = useQuery({ queryKey: ['system'], queryFn: () => api.get<SystemStats>('/settings/system') })

  return (
    <div>
      <PageHeader title="Storage" description="How your map storage is used." />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <HardDrive className="text-blue-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">Total map storage</p>
              <p className="text-2xl font-bold">{formatBytes(storage.data?.total_bytes ?? 0)}</p>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <p className="text-sm text-gray-500">Maps</p>
          <p className="text-2xl font-bold">{stats.data?.maps_count ?? 0}</p>
        </Card>
        <Card className="p-5">
          <p className="text-sm text-gray-500">Disk free</p>
          <p className="text-2xl font-bold">{formatBytes(stats.data?.disk_free_bytes ?? 0)}</p>
        </Card>
      </div>

      <h2 className="mt-8 mb-3 text-lg font-semibold">By region</h2>
      <Card className="overflow-hidden">
        {storage.data?.maps.map((r) => {
          const pct = storage.data.total_bytes ? (r.bytes / storage.data.total_bytes) * 100 : 0
          return (
            <div key={r.name} className="flex items-center gap-4 border-b border-gray-100 px-4 py-3 last:border-0">
              <div className="w-40 min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{r.name}</p>
                <p className="text-xs text-gray-400">{r.maps} map{r.maps === 1 ? '' : 's'}</p>
              </div>
              <div className="w-1/3">
                <ProgressBar value={pct} color="blue" />
              </div>
              <div className="w-24 text-right text-sm font-medium">{formatBytes(r.bytes)}</div>
              <div className="w-12 text-right text-xs text-gray-400">{pct.toFixed(1)}%</div>
            </div>
          )
        })}
      </Card>
    </div>
  )
}