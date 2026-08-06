import { useEffect, useState } from 'react'
import { toast } from 'react-hot-toast'
import { Map as MapIcon, Plus, Play, Pause, Trash2, ShieldAlert } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, ProgressBar, Select } from '@/components/ui'
import { api } from '@/lib/api'
import { formatBytes, formatEta, formatSpeed } from '@/lib/utils'
import type { DownloadEstimate, MapItem, Provider, Region } from '@/lib/types'

const statusTone: Record<string, string> = {
  complete: 'green',
  imported: 'green',
  downloading: 'blue',
  pending: 'yellow',
  paused: 'yellow',
  cancelled: 'gray',
  error: 'red',
}

export default function Maps() {
  const [wizardOpen, setWizardOpen] = useState(false)
  const [queryKey, setQueryKey] = useState(0)

  const maps = useQuery({
    queryKey: ['maps', queryKey],
    queryFn: () => api.get<MapItem[]>('/maps'),
    refetchInterval: 3000,
  })

  const actions = async (fn: () => Promise<unknown>) => {
    try {
      await fn()
      toast.success('Done')
      setQueryKey((k) => k + 1)
    } catch (e: any) {
      toast.error(e.detail || 'Failed')
    }
  }

  return (
    <div>
      <PageHeader
        title="Maps"
        description="Downloaded maps in your library."
        actions={<Button onClick={() => setWizardOpen(true)}><Plus size={16} /> New Map</Button>}
      />

      {wizardOpen && <NewMapWizard onClose={() => { setWizardOpen(false); setQueryKey((k) => k + 1) }} />}

      {maps.isLoading && <p className="text-sm text-gray-500">Loading maps…</p>}
      {maps.data?.length === 0 && (
        <EmptyState
          icon={<MapIcon size={48} />}
          title="No maps yet"
          description="Download your first offline map to start using Maparr."
          action={<Button onClick={() => setWizardOpen(true)}>Create your first map</Button>}
        />
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {maps.data?.map((m) => (
          <Card key={m.id} className="p-4">
            <div className="mb-2 flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-semibold">{m.name}</h3>
                <p className="text-xs text-gray-500">{m.provider_name} · z{m.min_zoom}–{m.max_zoom}</p>
              </div>
              <Badge tone={statusTone[m.status] ?? 'gray'}>{m.status}</Badge>
            </div>

            {['downloading', 'pending', 'paused'].includes(m.status) && (
              <div className="mb-3 space-y-1">
                <ProgressBar value={m.percent} color="blue" />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>{m.tiles_done.toLocaleString()} / {m.tiles_total.toLocaleString()} tiles</span>
                  <span>{formatSpeed(m.speed)}</span>
                </div>
                <div className="text-xs text-gray-400">ETA {formatEta(m.eta_seconds)} · {formatBytes(m.bytes_done)}</div>
              </div>
            )}

            {m.status === 'complete' && (
              <div className="mb-3 text-xs text-gray-500">
                {m.tiles_done.toLocaleString()} tiles · {formatBytes(m.file_size)}
                {!m.integrity_ok && <span className="ml-2 text-red-600">integrity issue</span>}
              </div>
            )}
            {m.status === 'imported' && (
              <div className="mb-3 text-xs text-gray-500">{m.tiles_done.toLocaleString()} tiles · imported</div>
            )}
            {m.status === 'error' && <p className="mb-3 text-xs text-red-600">{m.error}</p>}

            <div className="flex flex-wrap gap-2">
              {['pending', 'downloading'].includes(m.status) && (
                <Button size="sm" variant="outline" onClick={() => actions(() => api.post(`/maps/${m.id}/pause`))}>
                  <Pause size={14} /> Pause
                </Button>
              )}
              {m.status === 'paused' && (
                <Button size="sm" onClick={() => actions(() => api.post(`/maps/${m.id}/resume`))}>
                  <Play size={14} /> Resume
                </Button>
              )}
              {['error', 'cancelled'].includes(m.status) && (
                <Button size="sm" variant="outline" onClick={() => actions(() => api.post(`/maps/${m.id}/start`))}>
                  <Play size={14} /> Retry
                </Button>
              )}
              {['downloading', 'pending', 'paused'].includes(m.status) && (
                <Button size="sm" variant="outline" onClick={() => actions(() => api.post(`/maps/${m.id}/cancel`))}>
                  Cancel
                </Button>
              )}
              <Button size="sm" variant="danger" onClick={() => {
                if (window.confirm('Delete this map?')) actions(() => api.del(`/maps/${m.id}`))
              }}>
                <Trash2 size={14} /> Delete
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

/* ---------------- New Map Wizard ---------------- */

function NewMapWizard({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(0)
  const [providerId, setProviderId] = useState('')
  const [regionQ, setRegionQ] = useState('')
  const [regions, setRegions] = useState<Region[]>([])
  const [region, setRegion] = useState<Region | null>(null)
  const [minZoom, setMinZoom] = useState(8)
  const [maxZoom, setMaxZoom] = useState(15)
  const [estimate, setEstimate] = useState<DownloadEstimate | null>(null)
  const [estimating, setEstimating] = useState(false)

  const providers = useQuery({
    queryKey: ['providers'],
    queryFn: () => api.get<Provider[]>('/providers'),
  })

  useEffect(() => {
    if (providers.data && !providerId) {
      const base = providers.data.find((p) => p.kind === 'baselayer')
      setProviderId(base?.id ?? providers.data[0]?.id ?? '')
    }
  }, [providers.data, providerId])

  const searchRegions = async (q: string) => {
    setRegion(null)
    if (q.length < 2) return setRegions([])
    try {
      const res = await api.get<Region[]>(`/regions/search?q=${encodeURIComponent(q)}&limit=10`)
      setRegions(res)
    } catch {
      setRegions([])
    }
  }

  const estimateRegion = async () => {
    if (!region) return
    setEstimating(true)
    setEstimate(null)
    try {
      const est = await api.post<DownloadEstimate>('/maps/estimate', {
        provider_id: providerId,
        region_id: region.id,
        region_name: region.name,
        bbox: region.bbox,
        min_zoom: minZoom,
        max_zoom: maxZoom,
      })
      setEstimate(est)
      setStep(1)
    } catch (e: any) {
      toast.error(e.detail || 'Failed to estimate')
    } finally {
      setEstimating(false)
    }
  }

  const createMap = async () => {
    if (!region || !estimate) return
    try {
      const map = await api.post<MapItem>('/maps', {
        provider_id: providerId,
        region_id: region.id,
        region_name: region.name,
        bbox: region.bbox,
        min_zoom: minZoom,
        max_zoom: maxZoom,
      })
      toast.success('Map created')
      await api.post(`/maps/${map.id}/start`)
      onClose()
    } catch (e: any) {
      toast.error(e.detail || 'Failed to create map')
    }
  }

  return (
    <Modal open title="New Map" onClose={onClose}>
      {step === 0 && (
        <div className="space-y-4">
          <Select label="Provider (map style)" value={providerId} onChange={(e) => setProviderId(e.target.value)}>
            {providers.data?.map((p) => (
              <option key={p.id} value={p.id}>{p.name}{p.kind === 'overlay' ? ' (overlay)' : ''}</option>
            ))}
          </Select>

          <div>
            <p className="mb-1 text-sm font-medium text-gray-700">Region</p>
            <Input value={regionQ} onChange={(e) => { setRegionQ(e.target.value); searchRegions(e.target.value) }} placeholder="e.g. Germany, California, Berlin" />
            {regions.length > 0 && !region && (
              <ul className="mt-2 max-h-48 overflow-auto rounded-md border border-gray-200 dark:border-gray-700">
                {regions.map((r) => (
                  <li key={r.id}>
                    <button className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700" onClick={() => { setRegion(r); setRegionQ(r.name); setRegions([]) }}>
                      {r.name} <span className="text-xs text-gray-400">({r.kind})</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {region && <p className="mt-2 text-sm text-blue-600">Selected: {region.name}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Min zoom</label>
              <Input type="number" min={0} max={22} value={minZoom} onChange={(e) => setMinZoom(+e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Max zoom</label>
              <Input type="number" min={0} max={22} value={maxZoom} onChange={(e) => setMaxZoom(+e.target.value)} />
            </div>
          </div>

          <Button className="w-full" disabled={!region || estimating} onClick={estimateRegion}>
            {estimating ? 'Estimating…' : 'Estimate download size'}
          </Button>
          <p className="text-xs text-gray-500">You will see a size estimate before anything downloads.</p>
        </div>
      )}

      {step === 1 && estimate && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Estimated download for <strong>{region?.name}</strong> (z{minZoom}–{maxZoom})
          </p>
          <div className="rounded-lg bg-blue-50 p-4 text-center dark:bg-blue-900/40">
            <p className="text-3xl font-bold text-blue-700 dark:text-blue-300">{estimate.human_size}</p>
            <p className="text-sm text-gray-600 dark:text-gray-300">{estimate.tiles.toLocaleString()} tiles</p>
          </div>
          <div className="max-h-40 overflow-auto text-xs text-gray-500">
            {estimate.by_zoom.slice().reverse().map((z) => (
              <div key={z.zoom} className="flex justify-between border-b border-gray-100 py-1 dark:border-gray-700">
                <span>Zoom {z.zoom}</span><span>{z.tiles.toLocaleString()} tiles · {formatBytes(z.bytes)}</span>
              </div>
            ))}
          </div>
          {estimate.notes.map((n, i) => <p key={i} className="text-xs text-yellow-600">⚠ {n}</p>)}

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setStep(0)}>Back</Button>
            <Button onClick={createMap}>Start download</Button>
          </div>
        </div>
      )}
    </Modal>
  )
}