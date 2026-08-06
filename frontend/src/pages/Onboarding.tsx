import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/store'
import { Button, Card, Input } from '@/components/ui'

import { api } from '@/lib/api'
import toast from 'react-hot-toast'
import { Provider, MapItem } from "@/lib/types"

export default function Onboarding() {
  const navigate = useNavigate()
   const { login } = useAuth();
  const [step, setStep] = useState(0) // 0: welcome, 1: create admin, 2: optional map, 3: done
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const nextStep = () => setStep(s => s + 1)
  const prevStep = () => setStep(s => s - 1)

  const handleCreateAdmin = async () => {
    setLoading(true)
    try {
      // Create admin user via API (if not exists)
      // We'll attempt to register; if user exists, we'll just login.
      try {
        await api.post('/users', {
          username,
          email,
          password,
          role: 'admin',
        })
        toast.success('Admin account created')
      } catch (e: any) {
        // Might already exist; try to login
        if (e.response?.status !== 409) throw e
      }
      // Login
      await api.post('/auth/login', { username, password })
      // Set tokens via auth hook? We'll rely on login function from useAuth
      await login(username, password)
      toast.success('Logged in')
      nextStep()
    } catch (err: any) {
      toast.error(err.detail || 'Failed to create admin')
    } finally {
      setLoading(false)
    }
  }

  const handleSkip = () => {
    // Skip straight to dashboard
    navigate('/')
  }

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-gray-50 dark:bg-gray-900">
      <Card className="w-full max-w-md p-8 space-y-6">
        {step === 0 && (
          <>
            <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white">
              Welcome to Maparr
            </h2>
            <p className="text-center text-gray-600 dark:text-gray-300">
              Set up your self-hosted offline map server in a few steps.
            </p>
            <Button onClick={nextStep} className="w-full">
              Get Started
            </Button>
          </>
        )}
        {step === 1 && (
          <>
            <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white">
              Create Administrator Account
            </h2>
            <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); handleCreateAdmin(); }}>
              <Input
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Creating…' : 'Create Account'}
              </Button>
            </form>
            <Button variant="ghost" onClick={handleSkip} className="w-full">
              I already have an account, login
            </Button>
          </>
        )}
        {step === 2 && (
          <>
            <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white">
              Optional: Download a Starter Map
            </h2>
            <p className="text-center text-gray-600 dark:text-gray-300 mb-4">
              You can download a sample map now to get started quickly, or skip and add maps later.
            </p>
            <div className="space-y-4">
              <Button onClick={nextStep} className="w-full">
                Skip for now
              </Button>
              <Button
                onClick={async () => {
                  // For simplicity, we'll just create a map for world (bbox entire world) using osm provider
                  try {
                    // Get provider OSM standard
                    const providers = await api.get<Provider[]>('/providers')
                    const osm = providers.find((p: Provider) => p.id === 'osm-standard')
                    if (!osm) throw new Error('OSM provider not found')
                    const map = await api.post<MapItem>('/maps', {
                      provider_id: osm.id,
                      region_id: 'world',
                      region_name: 'World',
                      bbox: [-180, -85.0511, 180, 85.0511],
                      min_zoom: 0,
                      max_zoom: 2,
                    })
                    toast.success('World map download started')
                    // Start download
                    await api.post(`/maps/${map.id}/start`)
                  } catch (err: any) {
                    toast.error(err.detail || 'Failed to start sample download')
                  }
                  nextStep()
                }}
                className="w-full"
              >
                Download World Map (low zoom)
              </Button>
            </div>
          </>
        )}
        {step === 3 && (
          <>
            <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white">
              Setup Complete
            </h2>
            <p className="text-center text-gray-600 dark:text-gray-300">
              You're ready to explore your offline maps.
            </p>
            <Button onClick={() => navigate('/')} className="w-full">
              Go to Dashboard
            </Button>
          </>
        )}
      </Card>
    </div>
  )
}