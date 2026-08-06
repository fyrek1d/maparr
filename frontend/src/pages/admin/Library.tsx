import { useState } from 'react'
import { toast } from 'react-hot-toast'
import { useQuery } from '@tanstack/react-query'
import { Layers, Search, ShieldCheck, Trash2 } from 'lucide-react'

import { Badge, Button, Card, EmptyState, Input, PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import { formatBytes, formatDate } from '@/lib/utils'
import type { MapItem, IntegrityResult } from "@/lib/types"

export default function Library() {
  const [q, setQ] = useState('')
  const [tick, setTick] = useState(0)

  const maps = useQuery({
    queryKey: ['library', q, tick],
    queryFn: () => api.get<MapItem[]>(`/maps${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  })

  const library = (maps.data ?? []).filter((m) => m.status === 'complete' || m.status === 'imported')

  return (
    <div>
      <PageHeader title="Map Library" description="Browse and manage your downloaded maps." />
      <div className="mb-4 w-full max-w-sm">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search maps…" className="input w-full pl-9" />
        </div>
      </div>

      {library.length === 0 && (
        <EmptyState icon={<Layers size={48} />} title="No maps in library" description="Completed maps appear here and are instantly usable offline." />
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {library.map((m) => (
          <Card key={m.id} className="p-4">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-semibold">{m.name}</h3>
                <p className="text-xs text-gray-500">{m.region_name} · {m.provider_name}</p>
                <p className="mt-1 text-xs text-gray-400">
                  {formatBytes(m.file_size)} · {m.tiles_done.toLocaleString()} tiles · z{m.min_zoom}–{m.max_zoom}
                  {m.completed_at ? ` · ${formatDate(m.completed_at)}` : ''}
                </p>
              </div>
              <Badge tone={m.status === 'imported' ? 'purple' : 'green'}>{m.status === 'imported' ? 'imported' : 'complete'}</Badge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button size="sm" onClick={() => window.open(`/map/${m.id}`, '_blank')}>Open in viewer</Button>
              <Button size="sm" variant="outline" onClick={async () => {
                try {
                  const r = await api.post<IntegrityResult>(`/maps/${m.id}/integrity`)
                  toast.success(r.ok ? 'Integrity OK' : `Integrity issues: ${r.errors.length}`)
                  setTick((t) => t + 1)
                } catch (e: any) { toast.error(e.detail) }
              }}><ShieldCheck size={14} /> Verify</Button>
              <Button size="sm" variant="danger" onClick={async () => {
                if (!window.confirm('Delete this map?')) return
                try { await api.del(`/maps/${m.id}`); toast.success('Deleted'); setTick((t) => t + 1) } catch (e: any) { toast.error(e.detail) }
              }}><Trash2 size={14} /></Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}