import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/store'
import { Button, Card, Input, Select } from '@/components/ui'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { Bell, ShieldCheck, Map, Activity, ServerCog, Zap, X } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Settings() {
  const [loading, setLoading] = useState(true)
  const [ldapConfig, setLdapConfig] = useState({
    enabled: false,
    url: '',
    bind_dn: '',
    bind_password: '',
    user_base_dn: '',
    user_filter: '(uid={username})',
    user_attr_map: '{"username": "uid", "email": "mail"}',
    default_role: 'user',
  })
  const [oidcProviders, setOidcProviders] = useState<Array<any>>([]) // list of {id, name, issuer, client_id, client_secret, scope}
  const [showOidcModal, setShowOidcModal] = useState(false)
  const [editOidcIndex, setEditOidcIndex] = useState<number | null>(null)
  const [oidcForm, setOidcForm] = useState({
    id: '',
    name: '',
    issuer: '',
    client_id: '',
    client_secret: '',
    scope: 'openid profile email',
  })

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      setLoading(true)
      const ldapRes = await api.get('/settings/ldap')
      setLdapConfig(ldapConfig => ({ ...ldapConfig, ...(ldapRes || {}) }))
      const oidcRes = await api.get('/settings/oidc')
      setOidcProviders(Array.isArray(oidcRes) ? oidcRes : [])
    } catch (e) {
      // If endpoints not implemented yet, keep defaults
      console.warn('Settings endpoints not ready', e)
    } finally {
      setLoading(false)
    }
  }

  async function saveLdap() {
    try {
      await api.post('/settings/ldap', ldapConfig)
      toast.success('LDAP settings saved')
    } catch (err: any) {
      toast.error(err.detail || 'Failed to save LDAP')
    }
  }

  async function addOidcProvider() {
    try {
      await api.post('/settings/oidc', oidcForm)
      await loadSettings()
      setShowOidcModal(false)
      resetOidcForm()
      toast.success('OIDC provider added')
    } catch (err: any) {
      toast.error(err.detail || 'Failed to add provider')
    }
  }

  async function updateOidcProvider() {
    if (editOidcIndex === null) return
    try {
      const id = oidcProviders[editOidcIndex ?? 0].id
      await api.put(`/settings/oidc/${id}`, oidcForm)
      await loadSettings()
      setShowOidcModal(false)
      resetOidcForm()
      setEditOidcIndex(null)
      toast.success('OIDC provider updated')
    } catch (err: any) {
      toast.error(err.detail || 'Failed to update provider')
    }
  }

  async function deleteOidcProvider(id: string) {
    if (!window.confirm('Delete this OIDC provider?')) return
    try {
      await api.del(`/settings/oidc/${id}`)
      await loadSettings()
      toast.success('Provider deleted')
    } catch (err: any) {
      toast.error(err.detail || 'Failed to delete')
    }
  }

  function resetOidcForm() {
    setOidcForm({
      id: '',
      name: '',
      issuer: '',
      client_id: '',
      client_secret: '',
      scope: 'openid profile email',
    })
  }

  function handleOidcChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    const { name, value } = e.target
    setOidcForm(prev => ({ ...prev, [name]: value }))
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <div className="w-16 h-16 border-4 border-t-4 border-t-primary-500 border-gray-200 rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Refresh
        </Button>
      </div>

      {/* LDAP Settings */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <ServerCog size={24} className="text-blue-600" />
          <h2 className="text-lg font-semibold">LDAP / Active Directory</h2>
        </div>
          <div className="mb-4 flex items-center space-x-2">
            <input
              type="checkbox"
              checked={ldapConfig.enabled}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setLdapConfig({ ...ldapConfig, enabled: e.target.checked })}
              className="h-4 w-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
            />
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Enable LDAP authentication
            </span>
          </div>
        <div className="space-y-4">
          <Input
            label="LDAP Server URL"
            placeholder="ldap://ldap.example.com:389"
            value={ldapConfig.url}
            onChange={e => setLdapConfig({ ...ldapConfig, url: e.target.value })}
          />
          <Input
            label="Bind DN (optional)"
            placeholder="cn=admin,dc=example,dc=com"
            value={ldapConfig.bind_dn}
            onChange={e => setLdapConfig({ ...ldapConfig, bind_dn: e.target.value })}
          />
          <Input
            label="Bind Password"
            type="password"
            value={ldapConfig.bind_password}
            onChange={e => setLdapConfig({ ...ldapConfig, bind_password: e.target.value })}
          />
          <Input
            label="User Base DN"
            placeholder="ou=users,dc=example,dc=com"
            value={ldapConfig.user_base_dn}
            onChange={e => setLdapConfig({ ...ldapConfig, user_base_dn: e.target.value })}
          />
          <Input
            label="User Filter"
            placeholder="(uid={username})"
            value={ldapConfig.user_filter}
            onChange={e => setLdapConfig({ ...ldapConfig, user_filter: e.target.value })}
          />
          <Input
            label="User Attribute Mapping (JSON)"
            placeholder='{"username": "uid", "mail": "email"}'
            value={ldapConfig.user_attr_map}
            onChange={e => setLdapConfig({ ...ldapConfig, user_attr_map: e.target.value })}
          />
           <Select
             label="Default Role"
             value={ldapConfig.default_role}
             onChange={e => setLdapConfig({ ...ldapConfig, default_role: e.target.value })}
           >
            <option value="user">User</option>
            <option value="admin">Administrator</option>
          </Select>
          <div className="flex justify-end">
            <Button onClick={saveLdap}>Save LDAP Settings</Button>
          </div>
        </div>
      </Card>

      {/* OIDC Settings */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Zap size={24} className="text-yellow-600" />
          <h2 className="text-lg font-semibold">OpenID Connect (OIDC) / OAuth2</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setOidcForm({
                id: '',
                name: '',
                issuer: '',
                client_id: '',
                client_secret: '',
                scope: 'openid profile email',
              })
              setEditOidcIndex(null)
              setShowOidcModal(true)
            }}
          >
            Add Provider
          </Button>
        </div>

        <div className="space-y-4">
          {oidcProviders.length === 0 ? (
            <p className="text-gray-500">No OIDC providers configured.</p>
          ) : (
            <div className="space-y-2">
              {oidcProviders.map((p, idx) => (
                <div key={p.id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium">{p.name}</h3>
                      <p className="text-sm text-gray-500">{p.issuer}</p>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setOidcForm(p)
                          setEditOidcIndex(idx)
                          setShowOidcModal(true)
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => deleteOidcProvider(p.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* OIDC Modal */}
        <div className={`fixed inset-0 z-50 flex items-center justify-center ${showOidcModal ? 'block' : 'hidden'}`}>
          <div className="fixed inset-0 bg-black/50"></div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-96 max-w-full z-60">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-semibold">
                {editOidcIndex === null ? 'Add OIDC Provider' : 'Edit Oidc Provider'}
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowOidcModal(false)
                  resetOidcForm()
                  setEditOidcIndex(null)
                }}
              >
                <X size={20} />
              </Button>
            </div>
            <form onSubmit={e => {
              e.preventDefault()
              if (editOidcIndex === null) addOidcProvider()
              else updateOidcProvider()
            }} className="space-y-4">
              <Input
                label="Provider ID (unique)"
                value={oidcForm.id}
                onChange={e => setOidcForm({ ...oidcForm, id: e.target.value })}
                required
              />
              <Input
                label="Display Name"
                value={oidcForm.name}
                onChange={e => setOidcForm({ ...oidcForm, name: e.target.value })}
                required
              />
              <Input
                label="Issuer URL"
                placeholder="https://example.com/realms/myrealm"
                value={oidcForm.issuer}
                onChange={e => setOidcForm({ ...oidcForm, issuer: e.target.value })}
                required
              />
              <Input
                label="Client ID"
                value={oidcForm.client_id}
                onChange={e => setOidcForm({ ...oidcForm, client_id: e.target.value })}
                required
              />
              <Input
                label="Client Secret"
                type="password"
                value={oidcForm.client_secret}
                onChange={e => setOidcForm({ ...oidcForm, client_secret: e.target.value })}
              />
              <Input
                label="Scope"
                value={oidcForm.scope}
                onChange={e => setOidcForm({ ...oidcForm, scope: e.target.value })}
              />
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowOidcModal(false)
                    resetOidcForm()
                    setEditOidcIndex(null)
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={e => {
                    e.preventDefault()
                    if (editOidcIndex === null) addOidcProvider()
                    else updateOidcProvider()
                  }}
                >
                  {editOidcIndex === null ? 'Add Provider' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      </Card>

       {/* Notifications Settings (existing) - simplified placeholder */}
       <Card className="p-6">
         <div className="flex items-center gap-3 mb-4">
           <Bell size={24} className="text-red-500" />
           <h2 className="text-lg font-semibold">Notifications</h2>
         </div>
         <p className="text-sm text-gray-500 mb-4">
           Configure ntfy.sh, webhook, or other notification services via the
           <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">/settings/notification</code>
           endpoint or through the API.
         </p>
       </Card>

       {/* Maintenance & Backup (existing) - simplified placeholder */}
       <Card className="p-6">
         <div className="flex items-center gap-3 mb-4">
           <Activity size={24} className="text-green-600" />
           <h2 className="text-lg font-semibold">Maintenance & Backup</h2>
         </div>
         <div className="space-y-4">
           <Button onClick={() => {
             if (!window.confirm('Run maintenance now? (may take a moment)')) return
             // trigger via API
             fetch('/api/settings/maintenance', { method: 'POST' })
               .then(r => {
                 if (r.ok) toast.success('Maintenance triggered')
                 else throw new Error('Failed')
               })
               .catch(() => toast.error('Could not trigger maintenance'))
           }}>
             Run Maintenance Now
           </Button>
           <Button onClick={() => {
             if (!window.confirm('Create a backup of all data (including maps)?')) return
             fetch('/api/settings/backups?include_maps=true', { method: 'POST' })
               .then(r => {
                 if (r.ok) {
                   r.json().then(data => {
                     toast.success(`Backup created: ${data.name}`)
                   })
                 } else {
                   throw new Error('Failed')
                 }
               })
               .catch(() => toast.error('Backup failed'))
           }}>
             Create Backup
            </Button>
          </div>
        </Card>
      </div>
    );
  }