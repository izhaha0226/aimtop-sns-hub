"use client"
import { useEffect, useState } from "react"
import { Users, Eye, Heart, FileText, Sparkles } from "lucide-react"
import api from "@/services/api"
import { useSelectedClient } from "@/hooks/useSelectedClient"
import { channelsService, type ChannelConnection } from "@/services/channels"

interface Summary {
  followers: number
  followers_growth: number
  total_impressions: number
  avg_engagement_rate: number
  total_posts: number
}

interface ContentPerf {
  id: string
  title: string
  impressions: number
  engagement: number
  published_at: string
}

export default function AnalyticsPage() {
  const { selectedClientId, selectedClient, loading: clientLoading } = useSelectedClient()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [contents, setContents] = useState<ContentPerf[]>([])
  const [insights, setInsights] = useState("")
  const [period, setPeriod] = useState("30")
  const [loading, setLoading] = useState(true)
  const [insightLoading, setInsightLoading] = useState(false)
  const [channels, setChannels] = useState<ChannelConnection[]>([])

  useEffect(() => {
    if (clientLoading || !selectedClientId) return

    void Promise.resolve().then(() => {
      setLoading(true)
      const end = new Date().toISOString().split("T")[0]
      const start = new Date(Date.now() - parseInt(period) * 86400000).toISOString().split("T")[0]

      return channelsService.list(selectedClientId)
        .then(async (clientChannels) => {
        const connectedChannels = clientChannels.filter((channel) => channel.is_connected)
        setChannels(connectedChannels)
        const primaryChannelId = connectedChannels[0]?.id

        const summaryRes = primaryChannelId
          ? await api.get(`/api/v1/analytics/${primaryChannelId}/summary?start_date=${start}&end_date=${end}`).catch(() => ({ data: null }))
          : { data: null }
        const contentsRes = await api.get(`/api/v1/analytics/content-performance?client_id=${selectedClientId}&limit=10`).catch(() => ({ data: [] }))

        setSummary(summaryRes.data)
        const list = contentsRes.data?.items || contentsRes.data || []
        setContents(Array.isArray(list) ? list : [])
      })
        .catch(() => {
          setSummary(null)
          setContents([])
          setChannels([])
        })
        .finally(() => setLoading(false))
    })
  }, [period, selectedClientId, clientLoading])

  const visibleSummary = selectedClientId ? summary : null
  const visibleContents = selectedClientId ? contents : []
  const visibleChannels = selectedClientId ? channels : []

  const loadInsights = async () => {
    const primaryChannelId = visibleChannels[0]?.id
    if (!primaryChannelId) {
      setInsights("연결된 채널이 없어 인사이트를 생성할 수 없습니다.")
      return
    }

    setInsightLoading(true)
    api.get(`/api/v1/analytics/${primaryChannelId}/insights`)
      .then((r) => setInsights(r.data?.insights || r.data?.summary || JSON.stringify(r.data)))
      .catch(() => setInsights("인사이트를 불러올 수 없습니다."))
      .finally(() => setInsightLoading(false))
  }

  const kpis = visibleSummary ? [
    { label: "팔로워", value: visibleSummary.followers?.toLocaleString() || "0", icon: Users, change: visibleSummary.followers_growth },
    { label: "노출수", value: visibleSummary.total_impressions?.toLocaleString() || "0", icon: Eye },
    { label: "참여율", value: `${(visibleSummary.avg_engagement_rate || 0).toFixed(1)}%`, icon: Heart },
    { label: "게시물", value: visibleSummary.total_posts?.toLocaleString() || "0", icon: FileText },
  ] : []

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">분석</h1>
          {selectedClient && <p className="text-sm text-gray-500 mt-1">{selectedClient.name}</p>}
        </div>
        <div className="flex gap-2">
          {[{ v: "7", l: "7일" }, { v: "30", l: "30일" }, { v: "90", l: "90일" }].map((p) => (
            <button key={p.v} onClick={() => setPeriod(p.v)} className={`px-3 py-1.5 text-sm rounded-lg ${period === p.v ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>{p.l}</button>
          ))}
        </div>
      </div>

      {loading ? <p className="text-center text-gray-400">로딩 중...</p> : !selectedClientId ? (
        <div className="bg-white border rounded-lg p-6 text-sm text-gray-500">선택된 클라이언트가 없습니다.</div>
      ) : (
        <>
          {visibleChannels.length === 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-700 mb-6">
              연결된 채널이 없어 요약 지표와 AI 인사이트는 비어 있습니다.
            </div>
          )}
          <div className="grid grid-cols-4 gap-4 mb-6">
            {kpis.map((k) => (
              <div key={k.label} className="bg-white border rounded-lg p-4">
                <div className="flex items-center gap-2 text-gray-500 mb-1"><k.icon size={16} /><span className="text-xs">{k.label}</span></div>
                <p className="text-2xl font-bold">{k.value}</p>
                {k.change !== undefined && <p className={`text-xs mt-1 ${k.change >= 0 ? "text-green-600" : "text-red-600"}`}>{k.change >= 0 ? "+" : ""}{k.change}</p>}
              </div>
            ))}
          </div>
          <div className="bg-white border rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold">콘텐츠 성과 랭킹</h2>
            </div>
            {visibleContents.length === 0 ? <p className="text-gray-400 text-sm">데이터가 없습니다</p> : (
              <table className="w-full text-sm">
                <thead><tr className="text-left text-gray-500 border-b"><th className="pb-2">콘텐츠</th><th className="pb-2">노출</th><th className="pb-2">참여</th><th className="pb-2">발행일</th></tr></thead>
                <tbody>{visibleContents.map((c) => (
                  <tr key={c.id} className="border-b last:border-0">
                    <td className="py-2 font-medium">{c.title}</td>
                    <td className="py-2">{c.impressions?.toLocaleString()}</td>
                    <td className="py-2">{c.engagement?.toLocaleString()}</td>
                    <td className="py-2 text-gray-400">{c.published_at ? new Date(c.published_at).toLocaleDateString("ko") : "-"}</td>
                  </tr>
                ))}</tbody>
              </table>
            )}
          </div>
          <div className="bg-white border rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold flex items-center gap-2"><Sparkles size={16} /> AI 인사이트</h2>
              <button onClick={loadInsights} disabled={insightLoading || visibleChannels.length === 0} className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50">{insightLoading ? "분석 중..." : "AI 분석"}</button>
            </div>
            {insights && <p className="text-sm text-gray-700 whitespace-pre-wrap">{insights}</p>}
          </div>
        </>
      )}
    </div>
  )
}
