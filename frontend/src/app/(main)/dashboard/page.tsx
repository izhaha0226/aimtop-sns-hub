"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { FileText, Clock, Send, BookOpen, AlertCircle, ShieldAlert } from "lucide-react"
import api from "@/services/api"
import { STATUS_LABELS, STATUS_COLORS } from "@/types/content"
import type { ContentStatus } from "@/types/content"

interface DashboardStats {
  total_contents: number
  pending_approvals: number
  published_today: number
  scheduled: number
  drafts: number
}

interface ActivityItem {
  id: string
  title: string
  status: ContentStatus
  updated_at: string
  author_name?: string
}

interface ChannelsHealth {
  summary: {
    healthy: number
    expiring: number
    reauth_required: number
    unknown: number
  }
  items: Array<{
    id: string
    platform: string
    account_name?: string
    health: "healthy" | "expiring" | "reauth_required" | "unknown"
    token_expires_at?: string | null
  }>
}

export default function DashboardPage() {
  const router = useRouter()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [channelsHealth, setChannelsHealth] = useState<ChannelsHealth | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get("/api/v1/dashboard/stats"),
      api.get("/api/v1/dashboard/recent-activity"),
      api.get("/api/v1/dashboard/channels-health"),
    ])
      .then(([statsRes, activityRes, healthRes]) => {
        setStats(statsRes.data)
        const activityItems = Array.isArray(activityRes.data)
          ? activityRes.data
          : Array.isArray(activityRes.data?.recent_contents)
            ? activityRes.data.recent_contents
            : []
        setActivity(activityItems)
        setChannelsHealth(healthRes.data)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const statCards = stats
    ? [
        {
          label: "전체 콘텐츠",
          value: stats.total_contents,
          icon: FileText,
          color: "text-blue-600",
          bg: "bg-blue-50",
        },
        {
          label: "승인 대기",
          value: stats.pending_approvals,
          icon: Clock,
          color: "text-yellow-600",
          bg: "bg-yellow-50",
        },
        {
          label: "오늘 발행",
          value: stats.published_today,
          icon: Send,
          color: "text-green-600",
          bg: "bg-green-50",
        },
        {
          label: "예약됨",
          value: stats.scheduled,
          icon: BookOpen,
          color: "text-purple-600",
          bg: "bg-purple-50",
        },
        {
          label: "임시저장",
          value: stats.drafts,
          icon: AlertCircle,
          color: "text-gray-600",
          bg: "bg-gray-100",
        },
      ]
    : []

  const healthBadge = (health: "healthy" | "expiring" | "reauth_required" | "unknown") => {
    if (health === "healthy") return "bg-blue-50 text-blue-700"
    if (health === "expiring") return "bg-yellow-50 text-yellow-700"
    if (health === "reauth_required") return "bg-red-50 text-red-700"
    return "bg-gray-100 text-gray-600"
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">대시보드</h1>

      {loading ? (
        <div className="text-center py-12 text-gray-400">불러오는 중...</div>
      ) : (
        <>
          <div className="grid grid-cols-5 gap-4 mb-6">
            {statCards.map(({ label, value, icon: Icon, color, bg }) => (
              <div key={label} className="bg-white rounded-xl border p-4">
                <div className={`inline-flex p-2 rounded-lg ${bg} mb-3`}>
                  <Icon size={16} className={color} />
                </div>
                <p className="text-2xl font-bold text-gray-900">{value}</p>
                <p className="text-xs text-gray-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl border p-5 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-gray-700">채널 헬스 현황</h2>
                <p className="text-xs text-gray-400 mt-1">토큰 만료 및 재인증 필요 채널을 빠르게 확인합니다</p>
              </div>
              <div className="inline-flex p-2 rounded-lg bg-red-50">
                <ShieldAlert size={16} className="text-red-600" />
              </div>
            </div>

            <div className="grid grid-cols-4 gap-3 mb-4">
              <div className="rounded-lg bg-blue-50 px-4 py-3">
                <p className="text-xs text-blue-700">정상</p>
                <p className="text-xl font-bold text-blue-900">{channelsHealth?.summary.healthy ?? 0}</p>
              </div>
              <div className="rounded-lg bg-yellow-50 px-4 py-3">
                <p className="text-xs text-yellow-700">만료 임박</p>
                <p className="text-xl font-bold text-yellow-900">{channelsHealth?.summary.expiring ?? 0}</p>
              </div>
              <div className="rounded-lg bg-red-50 px-4 py-3">
                <p className="text-xs text-red-700">재인증 필요</p>
                <p className="text-xl font-bold text-red-900">{channelsHealth?.summary.reauth_required ?? 0}</p>
              </div>
              <div className="rounded-lg bg-gray-100 px-4 py-3">
                <p className="text-xs text-gray-600">미확인</p>
                <p className="text-xl font-bold text-gray-800">{channelsHealth?.summary.unknown ?? 0}</p>
              </div>
            </div>

            <div className="space-y-2">
              {(channelsHealth?.items || []).slice(0, 6).map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded-lg border px-3 py-2">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{item.platform}{item.account_name ? ` · ${item.account_name}` : ""}</p>
                    {item.token_expires_at && <p className="text-xs text-gray-400 mt-0.5">만료시각: {new Date(item.token_expires_at).toLocaleString("ko-KR")}</p>}
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${healthBadge(item.health)}`}>{item.health}</span>
                </div>
              ))}
              {(channelsHealth?.items || []).length === 0 && (
                <div className="text-sm text-gray-400 py-4 text-center">연결된 채널이 없습니다</div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border overflow-hidden">
            <div className="px-5 py-3 border-b">
              <h2 className="text-sm font-semibold text-gray-700">최근 활동</h2>
            </div>
            {activity.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">
                채널을 연동하고 첫 콘텐츠를 만들어보세요
              </div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {activity.map((item) => (
                  <li
                    key={item.id}
                    onClick={() => router.push(`/contents/${item.id}`)}
                    className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{item.title}</p>
                      {item.author_name && (
                        <p className="text-xs text-gray-400">{item.author_name}</p>
                      )}
                    </div>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium shrink-0 ${
                        STATUS_COLORS[item.status]
                      }`}
                    >
                      {STATUS_LABELS[item.status]}
                    </span>
                    <span className="text-xs text-gray-400 shrink-0">
                      {new Date(item.updated_at).toLocaleDateString("ko-KR")}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  )
}
