import React, { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-measure'
import 'leaflet/dist/images/marker-icon.png'
import 'leaflet/dist/images/marker-shadow.png'
import { PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import { SearchResult, MapItem } from "@/lib/types"
import { formatCoords } from '@/lib/utils'
import { Search } from 'lucide-react'
import { useAuth } from '@/store'

// Fix icon URLs (Vite)
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
})

export default function MapPage() {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null) // L.Map with extra controls
  const { mapId } = useParams<{ mapId: string }>()
  const { darkMode } = useAuth()

  const [mapData, setMapData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [coords, setCoords] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  useEffect(() => {
    let cancelled = false
    let mapInstance: any = null

    async function loadMap() {
      if (!mapContainerRef.current) return
      setLoading(true)
      setError(null)
      try {
        let detail: MapItem | null = null
        if (mapId) {
          detail = await api.get<MapItem>(`/maps/${mapId}`)
        } else {
           const maps = await api.get<MapItem[]>(`/maps?status=complete`)
          if (maps.length) detail = maps[0]
        }

        if (!detail) throw new Error('No map available')

        const center: [number, number] = [
          (detail.bbox[1] + detail.bbox[3]) / 2,
          (detail.bbox[0] + detail.bbox[2]) / 2,
        ]
        const zoom = Math.min(detail.max_zoom, Math.max(detail.min_zoom, 3))

        // Create leaflet map
        const map = L.map(mapContainerRef.current, {
          center,
          zoom,
          zoomControl: true,
          attributionControl: false,
        })

        // Base layer from maparr tile endpoint
        L.tileLayer('/api/tiles/{z}/{x}/{y}', {
          maxZoom: 22,
          minZoom: 0,
          attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map)

        // Add scale control
        L.control.scale({ imperial: false, metric: true }).addTo(map)

        // Add measure control
        const measureControl = (L as any).control.measure()
        measureControl.addTo(map)

        // Optional: add layer control for base/overlays (if any)
        // For now just a placeholder

        mapRef.current = map

        // Update coords on move
        map.on('moveend', () => {
          if (!cancelled) {
            const c = map.getCenter()
            setCoords(formatCoords(c.lat, c.lng))
          }
        })
        setCoords(formatCoords(center[0], center[1]))

        setMapData(detail)
      } catch (err: any) {
        setError(err.detail || err.message || 'Failed to load map')
        console.error('Map loading error:', err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadMap()
    return () => {
      cancelled = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [mapId])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (!q || !mapRef.current) return
    try {
      const results = await api.get<SearchResult[]>(`/search?q=${encodeURIComponent(q)}`)
      if (results.length) {
        const r = results[0]
        mapRef.current.setView([r.lat, r.lon], 12)
      }
    } catch {
      /* ignore */
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="w-16 h-16 border-4 border-t-4 border-t-primary-500 border-gray-200 rounded-full animate-spin"></div>
      </div>
    )
  }

  if (error || !mapData) {
    return (
      <div className="flex justify-center items-center min-h-screen text-red-500">
        Error: {error || 'Map data not available'}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen">
      <PageHeader
        title={mapData.name || 'Map Viewer'}
        description={`Provider: ${mapData.provider_name} | Region: ${mapData.region_name}`}
      />
      <div className="relative flex-1 overflow-hidden">
        <div ref={mapContainerRef} className="absolute inset-0" />
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2">
          <div className="relative w-64">
            <input
              type="text"
              placeholder="Search for locations…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="input w-full pl-8"
            />
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          </div>
          {coords && (
            <span className="text-sm text-gray-600 bg-white/80 px-2 py-1 rounded-md backdrop-blur-sm dark:bg-gray-800/80">
              {coords}
            </span>
          )}
        </div>
        {/* Attribution / controls bottom left */}
        <div className="absolute bottom-2 left-2 z-10 flex items-end gap-2 text-xs text-gray-500 dark:text-gray-400">
          {/* Leaflet attribution added by default, we can hide or customize */}
        </div>
      </div>
    </div>
  )
}