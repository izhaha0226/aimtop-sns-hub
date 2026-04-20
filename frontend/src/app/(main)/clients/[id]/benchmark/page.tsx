"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { benchmarkingService, type ActionLanguageProfileItem, type BenchmarkAccountItem, type BenchmarkPostItem, type RefreshAccountResult } from "@/services/benchmarking"

const PLATFORMS = ["instagram", "facebook", "x", "threads", "kakao", "tiktok", "linkedin", "youtube"]

const PLATFORM_HINTS: Record<string, string> = {
  instagram: "경쟁 인스타 username 입력. 실수집은 연결된 Instagram 채널 토큰이 필요합니다.",
  facebook: "페이지명 또는 page_id 입력. page_id는 metadata에 넣으면 더 안정적입니다.",
  x: "경쟁 X username 입력. 조회수는 공개 지표 프록시 추정입니다.",
  youtube: "채널 handle(@...) 또는 채널명 입력. metadata.channel_id가 있으면 더 정확합니다.",
  threads: "현재는 수동 수집 fallback만 지원합니다.",
  tiktok: "OAuth 연결은 있지만 벤치마킹 수집기는 아직 없습니다.",
  linkedin: "OAuth 연결은 있지만 공개 벤치마킹 수집기는 아직 없습니다.",
  kakao: "현재는 수동 수집 fallback만 지원합니다.",
}

const PLATFORM_SUPPORT: Record<string, string> = {
  instagram: "실수집 지원 · 조회수 프록시",
  facebook: "실수집 지원 · 조회수 프록시",
  x: "실수집 지원 · 조회수 프록시",
  youtube: "실수집 지원 · 실조회수",
  threads: "수동 fallback",
  tiktok: "미구현",
  linkedin: "미구현",
  kakao: "미구현",
}

function parseMetadata(platform: string, raw: string) {
  const value = raw.trim()
  if (!value) return undefined
  if (platform === "facebook") return { page_id: value }
  if (platform === "youtube") return { channel_id: value }
  return { external_id: value }
}

function metadataInputValue(platform: string, metadata?: Record<string, unknown> | null) {
  if (!metadata) return ""
  if (platform === "facebook") return String(metadata.page_id || "")
  if (platform === "youtube") return String(metadata.channel_id || "")
  return String(metadata.external_id || "")
}

function badgeTone(status?: string) {
  if (!status) return "bg-gray-100 text-gray-700 border-gray-200"
  if (status.includes("live_collected")) return "bg-green-50 text-green-700 border-green-200"
  if (status.includes("manual")) return "bg-amber-50 text-amber-700 border-amber-200"
  if (status.includes("error")) return "bg-red-50 text-red-700 border-red-200"
  return "bg-gray-100 text-gray-700 border-gray-200"
}

export default function ClientBenchmarkPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [accounts, setAccounts] = useState<BenchmarkAccountItem[]>([])
  const [topPosts, setTopPosts] = useState<BenchmarkPostItem[]>([])
  const [profile, setProfile] = useState<ActionLanguageProfileItem | null>(null)
  const [platform, setPlatform] = useState("instagram")
  const [topK, setTopK] = useState(10)
  const [windowDays, setWindowDays] = useState(30)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [refreshingId, setRefreshingId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [statusMap, setStatusMap] = useState<Record<string, RefreshAccountResult>>({})
  const [form, setForm] = useState({ handle: "", purpose: "all", source_type: "manual", memo: "", metadataInput: "" })
  const [editForm, setEditForm] = useState({ handle: "", purpose: "all", source_type: "manual", memo: "", metadataInput: "", is_active: true })

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

  async function handleCreateAccount() {
    if (!form.handle.trim()) return
    setSaving(true)
    try {
      const created = await benchmarkingService.createAccount({
        client_id: id,
        platform,
        handle: form.handle.trim(),
        purpose: form.purpose,
        source_type: form.source_type,
        memo: form.memo.trim() || undefined,
        metadata_json: parseMetadata(platform, form.metadataInput),
      })
      setAccounts((prev) => [created, ...prev])
      setForm({ handle: "", purpose: "all", source_type: "manual", memo: "", metadataInput: "" })
    } finally {
      setSaving(false)
    }
  }

  async function handleRefreshAccount(accountId: string) {
    setRefreshingId(accountId)
    try {
      const result = await benchmarkingService.refreshAccount(accountId, topK, windowDays)
      setStatusMap((prev) => ({ ...prev, [accountId]: result }))
      await load(platform, topK)
    } finally {
      setRefreshingId(null)
    }
  }

  function startEdit(item: BenchmarkAccountItem) {
    setEditingId(item.id)
    setEditForm({
      handle: item.handle,
      purpose: item.purpose,
      source_type: item.source_type,
      memo: item.memo || "",
      metadataInput: metadataInputValue(item.platform, item.metadata_json),
      is_active: item.is_active,
    })
  }

  async function saveEdit(item: BenchmarkAccountItem) {
    if (!editingId) return
    setSaving(true)
    try {
      const updated = await benchmarkingService.updateAccount(item.id, {
        handle: editForm.handle,
        purpose: editForm.purpose,
        source_type: editForm.source_type,
        memo: editForm.memo,
        is_active: editForm.is_active,
        metadata_json: parseMetadata(item.platform, editForm.metadataInput),
      })
      setAccounts((prev) => prev.map((row) => row.id === updated.id ? updated : row))
      setEditingId(null)
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(item: BenchmarkAccountItem) {
    const updated = await benchmarkingService.updateAccount(item.id, { is_active: !item.is_active })
    setAccounts((prev) => prev.map((row) => row.id === updated.id ? updated : row))
  }

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

      <div className="rounded-xl border bg-slate-50 px-4 py-3 text-xs text-slate-700">
        현재 지원 상태: {PLATFORM_SUPPORT[platform] || "미정"}
      </div>

      <div className="bg-white rounded-xl border p-5 space-y-4">
        <div>
          <div className="text-sm font-semibold">벤치마킹 계정 등록</div>
          <div className="text-xs text-gray-500 mt-1">{PLATFORM_HINTS[platform] || "채널별 실수집 가능 범위에 맞춰 등록하세요."}</div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <input value={form.handle} onChange={(e) => setForm((prev) => ({ ...prev, handle: e.target.value }))} placeholder="handle / username / page_id" className="rounded-lg border px-3 py-2 text-sm" />
          <select value={form.purpose} onChange={(e) => setForm((prev) => ({ ...prev, purpose: e.target.value }))} className="rounded-lg border px-3 py-2 text-sm">
            <option value="all">all</option>
            <option value="benchmark">benchmark</option>
            <option value="inspiration">inspiration</option>
          </select>
          <select value={form.source_type} onChange={(e) => setForm((prev) => ({ ...prev, source_type: e.target.value }))} className="rounded-lg border px-3 py-2 text-sm">
            <option value="manual">manual</option>
            <option value="discovery">discovery</option>
            <option value="competitor">competitor</option>
          </select>
          <input value={form.metadataInput} onChange={(e) => setForm((prev) => ({ ...prev, metadataInput: e.target.value }))} placeholder={platform === "facebook" ? "page_id (선택)" : platform === "youtube" ? "channel_id (선택)" : "보조 식별자 (선택)"} className="rounded-lg border px-3 py-2 text-sm" />
          <button onClick={handleCreateAccount} disabled={saving || !form.handle.trim()} className="rounded-lg bg-blue-600 text-white text-sm px-4 py-2 disabled:opacity-50">{saving ? "등록 중..." : "계정 등록"}</button>
        </div>
        <input value={form.memo} onChange={(e) => setForm((prev) => ({ ...prev, memo: e.target.value }))} placeholder="메모 (선택)" className="rounded-lg border px-3 py-2 text-sm w-full" />
      </div>

      <div className="bg-white rounded-xl border p-4 flex flex-wrap items-center gap-3">
        <label className="text-sm text-gray-600">Top-K</label>
        <input value={topK} onChange={(e) => setTopK(Number(e.target.value) || 10)} className="w-24 rounded-lg border px-3 py-2 text-sm" />
        <label className="text-sm text-gray-600">기간(일)</label>
        <input value={windowDays} onChange={(e) => setWindowDays(Number(e.target.value) || 30)} className="w-24 rounded-lg border px-3 py-2 text-sm" />
        <span className="text-xs text-gray-500">조회수/참여율/최근성 점수 기반</span>
      </div>

      {loading ? <div className="bg-white rounded-xl border p-6 text-sm text-gray-500">불러오는 중...</div> : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border p-4 lg:col-span-1">
              <h2 className="font-semibold mb-3">등록 계정</h2>
              <div className="space-y-3 text-sm">
                {platformAccounts.length === 0 ? <div className="text-gray-400">등록된 계정 없음</div> : platformAccounts.map((item) => {
                  const refreshState = statusMap[item.id]
                  const isEditing = editingId === item.id
                  return (
                    <div key={item.id} className="rounded-lg border px-3 py-3 space-y-2">
                      {isEditing ? (
                        <div className="space-y-2">
                          <input value={editForm.handle} onChange={(e) => setEditForm((prev) => ({ ...prev, handle: e.target.value }))} className="w-full rounded-lg border px-3 py-2 text-sm" />
                          <div className="grid grid-cols-2 gap-2">
                            <select value={editForm.purpose} onChange={(e) => setEditForm((prev) => ({ ...prev, purpose: e.target.value }))} className="rounded-lg border px-3 py-2 text-sm">
                              <option value="all">all</option>
                              <option value="benchmark">benchmark</option>
                              <option value="inspiration">inspiration</option>
                            </select>
                            <select value={editForm.source_type} onChange={(e) => setEditForm((prev) => ({ ...prev, source_type: e.target.value }))} className="rounded-lg border px-3 py-2 text-sm">
                              <option value="manual">manual</option>
                              <option value="discovery">discovery</option>
                              <option value="competitor">competitor</option>
                            </select>
                          </div>
                          <input value={editForm.metadataInput} onChange={(e) => setEditForm((prev) => ({ ...prev, metadataInput: e.target.value }))} placeholder={item.platform === "facebook" ? "page_id (선택)" : item.platform === "youtube" ? "channel_id (선택)" : "보조 식별자 (선택)"} className="w-full rounded-lg border px-3 py-2 text-sm" />
                          <input value={editForm.memo} onChange={(e) => setEditForm((prev) => ({ ...prev, memo: e.target.value }))} placeholder="메모" className="w-full rounded-lg border px-3 py-2 text-sm" />
                          <label className="flex items-center gap-2 text-xs text-gray-600">
                            <input type="checkbox" checked={editForm.is_active} onChange={(e) => setEditForm((prev) => ({ ...prev, is_active: e.target.checked }))} /> 활성화
                          </label>
                          <div className="flex gap-2">
                            <button onClick={() => void saveEdit(item)} disabled={saving} className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs disabled:opacity-50">저장</button>
                            <button onClick={() => setEditingId(null)} className="px-3 py-1.5 rounded-lg border text-xs">취소</button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="font-medium">{item.handle}</div>
                              <div className="text-xs text-gray-500">{item.purpose} / {item.source_type}</div>
                            </div>
                            <div className="flex gap-2">
                              <button onClick={() => startEdit(item)} className="px-2.5 py-1.5 rounded-lg border text-xs hover:bg-gray-50">수정</button>
                              <button onClick={() => void handleRefreshAccount(item.id)} disabled={refreshingId === item.id || !item.is_active} className="px-2.5 py-1.5 rounded-lg border text-xs hover:bg-gray-50 disabled:opacity-50">
                                {refreshingId === item.id ? "수집 중..." : "새로고침"}
                              </button>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${item.is_active ? "bg-blue-50 text-blue-700 border-blue-200" : "bg-gray-100 text-gray-600 border-gray-200"}`}>{item.is_active ? "활성" : "비활성"}</span>
                            <button onClick={() => void toggleActive(item)} className="text-[11px] text-gray-600 underline underline-offset-2">{item.is_active ? "비활성화" : "재활성화"}</button>
                          </div>
                          {item.metadata_json && (
                            <div className="text-[11px] text-gray-500 break-all">metadata: {JSON.stringify(item.metadata_json)}</div>
                          )}
                          {item.memo && <div className="text-[11px] text-gray-500">memo: {item.memo}</div>}
                          {refreshState && (
                            <div className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${badgeTone(refreshState.status)}`}>
                              {refreshState.status} · {refreshState.inserted}건
                            </div>
                          )}
                          {refreshState?.message && <div className="text-[11px] text-gray-600">{refreshState.message}</div>}
                        </>
                      )}
                    </div>
                  )
                })}
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
                      {post.post_url && <a href={post.post_url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 mt-1 inline-block">원문 보기</a>}
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
