import { toast } from 'react-hot-toast'
import { Download as DownloadIcon } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

import { Badge, Button, Card, EmptyState, PageHeader, ProgressBar } from '@/components/ui'
import { api } from '@/lib/api'
import { formatBytes, formatEta, formatSpeed } from '@/lib/utils'
import type { MapItem } from '@/lib/types'

export default function Downloads() {
  const queryKey = ['downloads', (window as any).__maparrTick ?? 0]

  const downloads = useQuery({
    queryKey,
    queryFn: () => api.get<MapItem[]>('/downloads/active'),
    refetchInterval: 2000,
  })

  return (
    <div>
      <PageHeader title="Downloads" description="Active and queued map downloads." />
      {downloads.isLoading && <p className="text-sm text-gray-500">Loading…</p>}
      {downloads.data?.length === 0 && (
        <EmptyState icon={<DownloadIcon size={48} />} title="No active downloads" description="Start a download from the Maps page." />
      )}

      <div className="space-y-3">
        {(downloads.data ?? []).map((d) => (
          <Card key={d.id} className="p-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DownloadIcon size={18} className="text-blue-600" />
                <span className="text-sm font-semibold">{d.name}</span>
              </div>
              <Badge tone={d.status === 'paused' ? 'yellow' : 'blue'}>{d.status}</Badge>
            </div>
            <ProgressBar value={d.percent} color={d.status === 'paused' ? 'yellow' : 'blue'} />
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
              <span>{d.tiles_done.toLocaleString()} / {d.tiles_total.toLocaleString()} tiles</span>
              <span>{formatBytes(d.bytes_done)}</span>
              <span>{formatSpeed(d.speed)}</span>
              <span>ETA {formatEta(d.eta_seconds)}</span>
              <span className="ml-auto">{d.percent}%</span>
            </div>
            <div className="mt-3 flex gap-2">
              {d.status === 'downloading' && (
                <Button size="sm" variant="outline" onClick={async () => { try { await api.post(`/maps/${d.id}/pause`); toast.success('Paused') } catch (e: any) { toast.error(e.detail) } }}>
                  Pause
                </Button>
              )}
              {d.status === 'paused' && (
                <Button size="sm" variant="outline" onClick={async () => { try { await api.post(`/maps/${d.id}/resume`); toast.success('Resumed') } catch (e: any) { toast.error(e.detail) } }}>
                  Resume
                </Button>
              )}
              {d.status !== 'complete' && (
                <Button size="sm" variant="danger" onClick={async () => { try { await api.post(`/maps/${d.id}/cancel`); toast.success('Cancelled') } catch (e: any) { toast.error(e.detail) } }}>
                  Cancel
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}