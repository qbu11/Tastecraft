import { useState, useEffect } from 'react'
import { UserPlus, Trash2, Shield } from 'lucide-react'
import { api } from '@/services/api'

interface TeamMember {
  id: number
  user_id: number
  email: string
  role: 'owner' | 'editor' | 'viewer'
  invited_at: string
  accepted_at: string | null
}

interface TeamData {
  team: { id: number; name: string; owner_id: number; created_at: string }
  members: TeamMember[]
}

const roleBadgeClasses: Record<string, string> = {
  owner: 'bg-amber-100 text-amber-800',
  editor: 'bg-blue-100 text-blue-800',
  viewer: 'bg-stone-100 text-stone-600',
}

const roleLabels: Record<string, string> = {
  owner: '管理员',
  editor: '编辑',
  viewer: '查看者',
}

export function TeamManagement() {
  const [teamData, setTeamData] = useState<TeamData | null>(null)
  const [loading, setLoading] = useState(true)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<'editor' | 'viewer'>('editor')
  const [creating, setCreating] = useState(false)
  const [teamName, setTeamName] = useState('')
  const [error, setError] = useState('')

  const fetchTeam = async () => {
    try {
      const { data } = await api.get<TeamData>('/v1/team/')
      setTeamData(data)
    } catch {
      setTeamData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTeam()
  }, [])

  const handleCreateTeam = async () => {
    if (!teamName.trim()) return
    setCreating(true)
    setError('')
    try {
      await api.post('/v1/team/', { name: teamName })
      setTeamName('')
      await fetchTeam()
    } catch {
      setError('创建团队失败')
    } finally {
      setCreating(false)
    }
  }

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return
    setError('')
    try {
      await api.post('/v1/team/invite', { email: inviteEmail, role: inviteRole })
      setInviteEmail('')
      await fetchTeam()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? '邀请失败')
    }
  }

  const handleRemove = async (userId: number) => {
    setError('')
    try {
      await api.delete(`/v1/team/members/${userId}`)
      await fetchTeam()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? '移除失败')
    }
  }

  const handleRoleChange = async (userId: number, role: string) => {
    setError('')
    try {
      await api.put(`/v1/team/members/${userId}/role`, { role })
      await fetchTeam()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? '修改角色失败')
    }
  }

  if (loading) {
    return <div className="py-8 text-center text-sm text-stone-400">加载中...</div>
  }

  // No team yet — show creation form
  if (!teamData) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-stone-800">创建团队</h3>
        <p className="text-xs text-stone-500">创建团队后可邀请成员协作管理内容。</p>
        <div className="flex gap-2">
          <input
            value={teamName}
            onChange={(e) => setTeamName(e.target.value)}
            placeholder="团队名称"
            className="flex-1 rounded-lg border border-stone-200 px-3 py-2 text-sm outline-none focus:border-[#c2714f]"
          />
          <button
            onClick={handleCreateTeam}
            disabled={creating || !teamName.trim()}
            className="rounded-lg bg-[#c2714f] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#b06a4a] disabled:opacity-50"
          >
            创建
          </button>
        </div>
        {error && <p className="text-xs text-red-500">{error}</p>}
      </div>
    )
  }

  const isOwner = teamData.members.some(
    (m) => m.role === 'owner',
  )

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-stone-800">
          <Shield size={14} className="mr-1.5 inline-block" />
          {teamData.team.name}
        </h3>
        <p className="mt-1 text-xs text-stone-500">
          {teamData.members.length} 位成员
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{error}</div>
      )}

      {/* Member list */}
      <div className="divide-y divide-stone-100 rounded-lg border border-stone-200">
        {teamData.members.map((member) => (
          <div key={member.id} className="flex items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-stone-800">{member.email}</p>
            </div>
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${roleBadgeClasses[member.role]}`}
            >
              {roleLabels[member.role]}
            </span>
            {isOwner && member.role !== 'owner' && (
              <>
                <select
                  value={member.role}
                  onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                  className="rounded border border-stone-200 px-2 py-1 text-xs outline-none"
                >
                  <option value="editor">编辑</option>
                  <option value="viewer">查看者</option>
                </select>
                <button
                  onClick={() => handleRemove(member.user_id)}
                  className="rounded p-1 text-stone-400 transition-colors hover:bg-red-50 hover:text-red-500"
                  title="移除成员"
                >
                  <Trash2 size={14} />
                </button>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Invite form */}
      {isOwner && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-stone-600">邀请新成员</h4>
          <div className="flex gap-2">
            <input
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              type="email"
              placeholder="输入邮箱地址"
              className="flex-1 rounded-lg border border-stone-200 px-3 py-2 text-sm outline-none focus:border-[#c2714f]"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as 'editor' | 'viewer')}
              className="rounded-lg border border-stone-200 px-2 py-2 text-sm outline-none"
            >
              <option value="editor">编辑</option>
              <option value="viewer">查看者</option>
            </select>
            <button
              onClick={handleInvite}
              disabled={!inviteEmail.trim()}
              className="flex items-center gap-1 rounded-lg bg-[#c2714f] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-[#b06a4a] disabled:opacity-50"
            >
              <UserPlus size={14} />
              邀请
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
