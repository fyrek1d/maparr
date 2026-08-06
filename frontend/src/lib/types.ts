/** TypeScript interfaces mirroring the Maparr REST API. */

export interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'user'
  is_active: boolean
  provider: string
  last_login_at: string | null
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface Provider {
  id: string
  name: string
  description: string
  kind: 'baselayer' | 'overlay'
  format: 'png' | 'jpg' | 'webp'
  min_zoom: number
  max_zoom: number
  subdomains: string[]
  attribution: string
  license: string
  license_url: string
  offline_allowed: boolean
  license_note: string
  requires_key: boolean
  has_key: boolean
  estimated_bytes_per_tile: number
  builtin: boolean
  url_template: string
}

export interface Region {
  id: string
  slug: string
  name: string
  kind: 'country' | 'admin1' | 'city' | 'custom'
  iso: string
  bbox: [number, number, number, number]
  centroid: [number, number]
  area_km2: number
  population: number
  meta: Record<string, string>
}

export interface SearchResult {
  name: string
  kind: string
  display_name: string
  lat: number
  lon: number
  bbox?: [number, number, number, number] | null
  population: number
  country: string
  admin1: string
}

export interface DownloadEstimate {
  tiles: number
  bytes_estimate: number
  bytes_estimate_high: number
  human_size: string
  by_zoom: { zoom: number; tiles: number; bytes: number }[]
  notes: string[]
}

export type MapStatus =
  | 'pending'
  | 'downloading'
  | 'paused'
  | 'cancelled'
  | 'complete'
  | 'error'
  | 'imported'

export interface MapItem {
  id: string
  name: string
  region_id: string
  region_name: string
  provider_id: string
  provider_name: string
  layer: string
  format: string
  min_zoom: number
  max_zoom: number
  bbox: [number, number, number, number]
  status: MapStatus
  error: string
  tiles_total: number
  tiles_done: number
  bytes_total: number
  bytes_done: number
  speed: number
  eta_seconds: number
  file_size: number
  checksum: string
  integrity_ok: boolean
  percent: number
  started_at: string | null
  completed_at: string | null
  paused_at: string | null
  created_at: string
}

export interface MapDetail extends MapItem {
  overlays: MapLayer[]
}

export interface MapLayer {
  id: string
  map_id: string
  name: string
  kind: string
  enabled: boolean
  max_zoom: number
}

export interface Bookmark {
  id: string
  name: string
  lat: number
  lon: number
  zoom: number
  is_favorite: boolean
  color: string
  description: string
  share_token: string
  created_at: string
}

export interface Marker {
  id: string
  name: string
  lat: number
  lon: number
  description: string
  color: string
  icon: string
  created_at: string
}

export interface Webhook {
  id: string
  name: string
  url: string
  events: string[]
  is_active: boolean
  last_delivery_at: string | null
  last_delivery_status: number
  created_at: string
}

export interface BackupEntry {
  name: string
  path: string
  created_at: string
  maps: number
  bytes: number
}

export interface StorageBreakdown {
  total_bytes: number
  total_human: string
  maps: { name: string; bytes: number; maps: number }[]
}

export interface SystemStats {
  maps_count: number
  total_bytes: number
  by_provider: { name: string; bytes: number; maps: number }[]
  by_region: { name: string; bytes: number; maps: number }[]
  active_downloads: number
  tiles_served: number
  tile_cache_hit_rate: number
  db_size_bytes: number
  disk_free_bytes: number
  uptime_seconds: number
}

export interface OnboardingStatus {
  setup_complete: boolean
  users_exist: boolean
  settings_configured: boolean
  next_steps: string[]
}