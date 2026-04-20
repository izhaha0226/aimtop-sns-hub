"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { benchmarkingService, type ActionLanguageProfileItem, type BenchmarkAccountItem, type BenchmarkPostItem } from "@/services/benchmarking"

const PLATFORMS = ["instagram", "facebook", "x", "threads", "kakao", "tiktok", "linkedin", "youtube"]

export default function ClientBenchmarkPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [accounts, setAccounts] = useState<BenchmarkAccountItem[]>([])
  const [topPosts, setTopPosts] = useState<BenchmarkPostItem[]>([])
  const [profile, setProfile] = useState<ActionLanguageProfileItem | null>(null)
  const [platform, setPlatform] = useState("instagram")
  const [topK, setTopK] = useState(10)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (currentPlatform = platform, currentTopK = topK) => {
    setLoading(true)
    try {
      const [accountRows, topPostRows, profileRow] = await Promise.all([
        benchmarkingService.listAccounts(id),
        benchmarkingService.getTopPosts(id, currentPlatform, currentTopK),
        benchmarkingService.getActionProfile(id, currentPlatform),
      ])
      setAccounts(accountRows)
      setTopPosts(topPostRows)
      setProfile(profileRow)
    } finally {
      setLoading(false)
    }
  }, [id, platform, topK])

  useEffect(() => { void load() }, [load])

  useEffect(() => { void load(platform, topK) }, [load, platform, topK])

  const platformAccounts = useMemo(() => accounts.filter((item) => item.platform === platform), [accounts, platform])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">벤치마킹 센터</h1>
          <p className="text-sm text-gray-500 mt-1">채널별 Top-K 콘텐츠와 액션 랭귀지 패턴을 확인합니다.</p>
        </div>
        <button onClick={() => router.push(`/clients/${id}`)} className="px-4 py-2 rounded-lg border text-sm hover:bg-gray-50">클라이언트 상세로</button>
      </div>

      <div className="flex flex-wrap gap-2">
        {PLATFORMS.map((item) => (
          <button
            key={item}
            onClick={() => setPlatform(item)}
            className={`px-3 py-2 rounded-lg text-sm ${platform === item ? "bg-blue-50 text-blue-700 font-medium" : "bg-white border text-gray-600"}`}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border p-4 flex items-center gap-3">
        <label className="text-sm text-gray-600">Top-K</label>
        <input value={topK} onChange={(e) => setTopK(Number(e.target.value) || 10)} className="w-24 rounded-lg border px-3 py-2 text-sm" />
        <span className="text-xs text-gray-500">조회수/참여율/최근성 점수 기반</span>
      </div>

      {loading ? <div className="bg-white rounded-xl border p-6 text-sm text-gray-500">불러오는 중...</div> : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border p-4 lg:col-span-1">
              <h2 className="font-semibold mb-3">등록 계정</h2>
              <div className="space-y-2 text-sm">
                {platformAccounts.length === 0 ? <div className="text-gray-400">등록된 계정 없음</div> : platformAccounts.map((item) => (
                  <div key={item.id} className="rounded-lg border px-3 py-2">
                    <div className="font-medium">{item.handle}</div>
                    <div className="text-xs text-gray-500">{item.purpose} / {item.source_type}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border p-4 lg:col-span-2">
              <h2 className="font-semibold mb-3">액션 랭귀지 프로필</h2>
              {!profile ? <div className="text-sm text-gray-400">아직 프로필이 없습니다.</div> : (
                <div className="space-y-4 text-sm">
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Top Hooks</div>
                    <div className="flex flex-wrap gap-2">{(profile.top_hooks_json || []).map((item) => <span key={item.pattern} className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs">{item.pattern} ({item.count})</span>)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Top CTAs</div>
                    <div className="flex flex-wrap gap-2">{(profile.top_ctas_json || []).map((item) => <span key={item.pattern} className="px-2 py-1 bg-yellow-50 text-yellow-700 rounded-full text-xs">{item.pattern} ({item.count})</span>)}</div>
                  </div>
                  <div className="rounded-lg border bg-gray-50 p-3 text-gray-700">{profile.recommended_prompt_rules || "추천 규칙 없음"}</div>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border overflow-hidden">
            <div className="px-4 py-3 border-b bg-gray-50 font-semibold text-sm">Top Posts</div>
            <div className="divide-y">
              {topPosts.length === 0 ? <div className="p-4 text-sm text-gray-400">Top post 데이터가 없습니다.</div> : topPosts.map((post, index) => (
                <div key={post.id} className="p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-medium text-sm">#{index + 1} {post.hook_text || post.content_text?.slice(0, 60) || "제목 없음"}</div>
                      <div className="text-xs text-gray-500 mt-1">CTA: {post.cta_text || "없음"}</div>
                    </div>
                    <div className="text-right text-xs text-gray-500">
                      <div>조회수 {post.view_count.toLocaleString()}</div>
                      <div>참여율 {post.engagement_rate}%</div>
                      <div>점수 {post.benchmark_score}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
