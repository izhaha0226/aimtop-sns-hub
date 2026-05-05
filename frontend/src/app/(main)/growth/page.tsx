"use client"

import { useState } from "react"
import { Clock, Lightbulb, MessageCircle, Repeat2, Send, Sparkles, Target, TrendingUp, Users } from "lucide-react"
import { useSelectedClient } from "@/hooks/useSelectedClient"
import api from "@/services/api"

type ViralExperiment = {
  name: string
  format: string
  hook: string
  cta: string
  measurement: string
}

type ViralStage = {
  stage: string
  mechanic: string
}

type ViralStrategy = {
  strategy_name: string
  strategic_thesis: string
  data_warning?: string
  signal_summary: {
    sample_size: number
    viral_score: number
    share_rate: number
    save_rate: number
    comment_rate: number
    top_hashtags: string[]
    top_hooks: string[]
    top_formats: { format: string; count: number }[]
  }
  viral_loop: { stages: ViralStage[] }
  content_experiments: ViralExperiment[]
  recommended_hashtags: string[]
  measurement: {
    primary_metrics: string[]
    guardrails: string[]
    next_review_cadence: string
  }
}

const asArray = <T,>(value: unknown): T[] => Array.isArray(value) ? value as T[] : []
const toPercent = (value?: number) => `${(((value || 0) * 100)).toFixed(1)}%`

export default function GrowthPage() {
  const { selectedClientId, selectedClient, loading: clientLoading } = useSelectedClient()
  const [platform, setPlatform] = useState("instagram")
  const [viralStrategy, setViralStrategy] = useState<ViralStrategy | null>(null)
  const [hashtags, setHashtags] = useState<{ hashtag?: string; popularity?: string; reason?: string }[]>([])
  const [ideas, setIdeas] = useState<Record<string, string>[]>([])
  const [competitor, setCompetitor] = useState("")
  const [competitorResult, setCompetitorResult] = useState<string>("")
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  const load = async (key: string, fn: () => Promise<void>) => {
    setLoading(prev => ({ ...prev, [key]: true }))
    try {
      await fn()
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }))
    }
  }

  const loadViralStrategy = () => load("viral", async () => {
    if (!selectedClientId) return
    const res = await api.get(`/api/v1/growth/viral-strategy?client_id=${selectedClientId}&platform=${platform}`)
    setViralStrategy(res.data?.data || null)
  })

  if (clientLoading) {
    return <div className="p-6 text-sm text-gray-500">클라이언트 정보를 불러오는 중...</div>
  }

  if (!selectedClientId) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-3">Growth Hub</h1>
        <div className="rounded-xl border bg-white p-6 text-sm text-gray-600">
          바이럴 전략은 선택 클라이언트 기준으로만 계산합니다. 먼저 상단에서 클라이언트를 선택해주세요.
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-purple-600">Supermarketing Viral Part</p>
          <h1 className="text-2xl font-bold">Growth Hub · 바이럴 루프 설계</h1>
          <p className="text-sm text-gray-500 mt-1">
            {selectedClient?.name || "선택 클라이언트"}의 벤치마크 반응을 기반으로 저장·공유·댓글 참여가 일어나는 SNS 운영안을 만듭니다.
          </p>
        </div>
        <div className="flex gap-2">
          <select value={platform} onChange={e => setPlatform(e.target.value)} className="rounded-lg border px-3 py-2 text-sm bg-white">
            <option value="instagram">Instagram</option>
            <option value="facebook">Facebook</option>
            <option value="threads">Threads</option>
            <option value="x">X</option>
          </select>
          <button onClick={loadViralStrategy} disabled={loading.viral} className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
            {loading.viral ? "분석 중..." : "바이럴 전략 생성"}
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-xl border bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500"><TrendingUp size={16}/> 바이럴 점수</div>
          <div className="mt-2 text-2xl font-bold">{viralStrategy?.signal_summary.viral_score ?? "-"}</div>
          <p className="text-xs text-gray-400">공유·저장·댓글·벤치마크 종합</p>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500"><Send size={16}/> 공유율</div>
          <div className="mt-2 text-2xl font-bold">{toPercent(viralStrategy?.signal_summary.share_rate)}</div>
          <p className="text-xs text-gray-400">share / view</p>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500"><Sparkles size={16}/> 저장률</div>
          <div className="mt-2 text-2xl font-bold">{toPercent(viralStrategy?.signal_summary.save_rate)}</div>
          <p className="text-xs text-gray-400">save / view</p>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500"><MessageCircle size={16}/> 댓글률</div>
          <div className="mt-2 text-2xl font-bold">{toPercent(viralStrategy?.signal_summary.comment_rate)}</div>
          <p className="text-xs text-gray-400">comment / view</p>
        </div>
      </div>

      {viralStrategy && (
        <>
          {viralStrategy.data_warning && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{viralStrategy.data_warning}</div>}

          <section className="rounded-xl border bg-white p-5">
            <h2 className="font-semibold flex items-center gap-2"><Repeat2 size={17}/> 바이럴 루프</h2>
            <p className="mt-2 text-sm text-gray-600">{viralStrategy.strategic_thesis}</p>
            <div className="mt-4 grid gap-3 md:grid-cols-5">
              {viralStrategy.viral_loop.stages.map(stage => (
                <div key={stage.stage} className="rounded-lg bg-purple-50 p-3">
                  <div className="text-sm font-semibold text-purple-900">{stage.stage}</div>
                  <div className="mt-1 text-xs text-purple-700">{stage.mechanic}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border bg-white p-5">
            <h2 className="font-semibold flex items-center gap-2"><Lightbulb size={17}/> 바로 테스트할 콘텐츠 실험</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {viralStrategy.content_experiments.map(experiment => (
                <div key={experiment.name} className="rounded-lg border p-4">
                  <div className="text-sm font-semibold">{experiment.name}</div>
                  <div className="mt-1 text-xs text-gray-500">포맷: {experiment.format} · 지표: {experiment.measurement}</div>
                  <div className="mt-3 text-sm text-gray-700">훅: {experiment.hook}</div>
                  <div className="mt-2 rounded bg-gray-50 p-2 text-sm text-gray-700">CTA: {experiment.cta}</div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-xl border bg-white p-5">
          <h2 className="font-semibold flex items-center gap-2 mb-3"><TrendingUp size={16}/> 트렌딩 해시태그</h2>
          <button onClick={() => load("hash", async () => {
            const res = await api.get(`/api/v1/growth/trending-hashtags?platform=${platform}&category=${selectedClient?.industry_category || ""}`)
            setHashtags(asArray(res.data?.data))
          })} disabled={loading.hash} className="mb-3 rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
            {loading.hash ? "분석 중..." : "트렌딩 분석"}
          </button>
          <div className="flex flex-wrap gap-2">
            {hashtags.map((item, index) => <span key={`${item.hashtag}-${index}`} className="rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-700">{item.hashtag}</span>)}
          </div>
        </div>

        <div className="rounded-xl border bg-white p-5">
          <h2 className="font-semibold flex items-center gap-2 mb-3"><Users size={16}/> 콘텐츠 아이디어</h2>
          <button onClick={() => load("ideas", async () => {
            const res = await api.post("/api/v1/growth/content-ideas", { client_id: selectedClientId, count: 5 })
            setIdeas(asArray(res.data?.data))
          })} disabled={loading.ideas} className="mb-3 rounded-lg bg-purple-600 px-3 py-1.5 text-sm text-white hover:bg-purple-700 disabled:opacity-50">
            {loading.ideas ? "생성 중..." : "아이디어 생성"}
          </button>
          <ul className="space-y-2">
            {ideas.map((idea, index) => <li key={index} className="text-sm text-gray-700"><span className="font-medium">{idea.title}</span><br/><span className="text-xs text-gray-500">{idea.description}</span></li>)}
          </ul>
        </div>

        <div className="rounded-xl border bg-white p-5">
          <h2 className="font-semibold flex items-center gap-2 mb-3"><Target size={16}/> 경쟁사 분석</h2>
          <div className="flex gap-2 mb-3">
            <input value={competitor} onChange={e => setCompetitor(e.target.value)} placeholder="@competitor" className="min-w-0 flex-1 rounded-lg border px-3 py-1.5 text-sm" />
            <button onClick={() => load("comp", async () => {
              const res = await api.post("/api/v1/growth/competitor-analysis", { competitor_handles: [competitor] })
              setCompetitorResult(JSON.stringify(res.data?.data || res.data, null, 2))
            })} disabled={loading.comp || !competitor} className="rounded-lg bg-orange-600 px-3 py-1.5 text-sm text-white hover:bg-orange-700 disabled:opacity-50">
              분석
            </button>
          </div>
          {competitorResult && <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded bg-gray-50 p-3 text-xs text-gray-600">{competitorResult}</pre>}
        </div>
      </div>

      <section className="rounded-xl border bg-white p-5">
        <h2 className="font-semibold flex items-center gap-2"><Clock size={16}/> 운영 기준</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <div className="rounded-lg bg-gray-50 p-3 text-sm">1주 1회: 공유율/저장률 낮은 훅 교체</div>
          <div className="rounded-lg bg-gray-50 p-3 text-sm">2주 1회: 댓글에서 다음 카드뉴스 소재 추출</div>
          <div className="rounded-lg bg-gray-50 p-3 text-sm">월 1회: 벤치마크 상위 포맷 재수집</div>
        </div>
      </section>
    </div>
  )
}
