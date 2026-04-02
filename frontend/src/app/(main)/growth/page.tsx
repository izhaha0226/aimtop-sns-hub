"use client"
import { useState } from "react"
import { TrendingUp, Lightbulb, Target, Clock, Sparkles } from "lucide-react"
import api from "@/services/api"

export default function GrowthPage() {
  const [hashtags, setHashtags] = useState<string[]>([])
  const [ideas, setIdeas] = useState<string[]>([])
  const [competitor, setCompetitor] = useState("")
  const [competitorResult, setCompetitorResult] = useState<string>("")
  const [bestTimes, setBestTimes] = useState<string>("")
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  const load = async (key: string, fn: () => Promise<void>) => {
    setLoading(prev => ({...prev, [key]: true}))
    try { await fn() } catch {}
    setLoading(prev => ({...prev, [key]: false}))
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Growth Hub</h1>
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white border rounded-lg p-5">
          <h2 className="font-semibold flex items-center gap-2 mb-3"><TrendingUp size={16}/> 트렌딩 해시태그</h2>
          <button onClick={() => load("hash", async () => {
            const r = await api.get("/api/v1/growth/trending-hashtags?platform=instagram")
            setHashtags(r.data?.hashtags || r.data || [])
          })} disabled={loading.hash} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 mb-3">
            {loading.hash ? "분석 중..." : "트렌딩 분석"}
          </button>
          {hashtags.length > 0 && <div className="flex flex-wrap gap-2">{hashtags.map((h,i) => <span key={i} className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs">#{h}</span>)}</div>}
        </div>

        <div className="bg-white border rounded-lg p-5">
          <h2 className="font-semibold flex items-center gap-2 mb-3"><Lightbulb size={16}/> 콘텐츠 아이디어</h2>
          <button onClick={() => load("ideas", async () => {
            const r = await api.post("/api/v1/growth/content-ideas", { count: 5 })
            setIdeas(r.data?.ideas || r.data || [])
          })} disabled={loading.ideas} className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 mb-3">
            {loading.ideas ? "생성 중..." : "아이디어 생성"}
          </button>
          {ideas.length > 0 && <ul className="space-y-2">{ideas.map((idea,i) => <li key={i} className="text-sm text-gray-700 flex items-start gap-2"><Sparkles size={14} className="text-purple-500 mt-0.5 shrink-0"/>{typeof idea === "string" ? idea : JSON.stringify(idea)}</li>)}</ul>}
        </div>

        <div className="bg-white border rounded-lg p-5">
          <h2 className="font-semibold flex items-center gap-2 mb-3"><Target size={16}/> 경쟁사 분석</h2>
          <div className="flex gap-2 mb-3">
            <input value={competitor} onChange={e => setCompetitor(e.target.value)} placeholder="경쟁사 핸들 (예: @competitor)" className="flex-1 text-sm border rounded-lg px-3 py-1.5"/>
            <button onClick={() => load("comp", async () => {
              const r = await api.post("/api/v1/growth/competitor-analysis", { competitor_handles: [competitor] })
              setCompetitorResult(r.data?.analysis || JSON.stringify(r.data, null, 2))
            })} disabled={loading.comp || !competitor} className="px-3 py-1.5 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50">
              {loading.comp ? "분석 중..." : "분석"}
            </button>
          </div>
          {competitorResult && <pre className="text-xs text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded">{competitorResult}</pre>}
        </div>

        <div className="bg-white border rounded-lg p-5">
          <h2 className="font-semibold flex items-center gap-2 mb-3"><Clock size={16}/> 최적 발행 시간</h2>
          <button onClick={() => load("times", async () => {
            const r = await api.get("/api/v1/growth/optimal-schedule")
            setBestTimes(r.data?.recommendation || JSON.stringify(r.data, null, 2))
          })} disabled={loading.times} className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 mb-3">
            {loading.times ? "분석 중..." : "최적 시간 추천"}
          </button>
          {bestTimes && <pre className="text-xs text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded">{bestTimes}</pre>}
        </div>
      </div>
    </div>
  )
}
