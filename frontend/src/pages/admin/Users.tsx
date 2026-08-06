import { useState } from 'react'
import { toast } from 'react-hot-toast'
import { useQuery } from '@tanstack/react-query'
import { UserPlus, Trash2, ToggleLeft } from 'lucide-react'

import { Badge, Button, Card, Input, Modal, PageHeader, Select } from '@/components/ui'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import type { User } from '@/lib/types'

export default function Users() {
  const [open, setOpen] = useState(false)
  const [tick, setTick] = useState(0)

  const users = useQuery({ queryKey: ['users', tick], queryFn: () => api.get<User[]>('/users') })

  return (
    <div>
      <PageHeader
        title="Users"
        description="Manage user accounts and roles."
        actions={<Button onClick={() => setOpen(true)}><UserPlus size={16} /> Add user</Button>}
      />
      <Card className="overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-xs text-gray-500">
            <tr>
              <th className="px-4 py-2">Username</th>
              <th className="px-4 py-2">Role</th>
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2 hidden md:table-cell">Last login</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {users.data?.map((u) => (
              <tr key={u.id} className="border-b border-gray-100 last:border-0">
                <td className="px-4 py-3 font-medium">{u.username}</td>
                <td className="px-4 py-3"><Badge tone={u.role === 'admin' ? 'purple' : 'gray'}>{u.role}</Badge></td>
                <td className="px-4 py-3 text-gray-500">{u.email || '—'}</td>
                <td className="px-4 py-3 text-gray-400">{formatDate(u.last_login_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    <button
                      className="text-gray-400 hover:text-blue-600"
                      title="Move to admin"
                      onClick={async () => { try { await api.patch(`/users/${u.id}`, { role: u.role === 'admin' ? 'user' : 'admin' }); toast.success('Role updated'); setTick((t) => t + 1) } catch (e: any) { toast.error(e.detail) } }}
                    ><ToggleLeft size={16} /></button>
                    <button
                      className="text-gray-400 hover:text-red-600"
                      onClick={async () => { if (!window.confirm('Delete user?')) return; try { await api.del(`/users/${u.id}`); toast.success('Deleted'); setTick((t) => t + 1) } catch (e: any) { toast.error(e.detail) } }}
                    ><Trash2 size={16} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <AddUserModal open={open} onClose={() => setOpen(false)} onDone={() => { setOpen(false); setTick((t) => t + 1) }} />
    </div>
  )
}

function AddUserModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('user')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.post('/users', { username, email, password, role })
      toast.success('User created')
      setUsername(''); setEmail(''); setPassword(''); setRole('user')
      onDone()
    } catch (err: any) {
      toast.error(err.detail || 'Failed to create user')
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add user" footer={
      <><Button variant="ghost" onClick={onClose}>Cancel</Button><Button form="add-user" type="submit">Create</Button></>
    }>
      <form id="add-user" onSubmit={submit} className="space-y-4">
        <Input label="Username" required value={username} onChange={(e) => setUsername(e.target.value)} />
        <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Input label="Password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        <Select label="Role" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="user">User</option>
          <option value="admin">Administrator</option>
        </Select>
      </form>
    </Modal>
  )
}