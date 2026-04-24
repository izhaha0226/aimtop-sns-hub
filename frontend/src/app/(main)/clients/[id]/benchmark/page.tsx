"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { benchmarkingService, type ActionLanguageProfileItem, type BenchmarkAccountDiagnosticItem, type BenchmarkAccountItem, type BenchmarkPostItem, type RefreshAccountResult } from "@/services/benchmarking"

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

const PLATFORM_SUPPORT_LEVEL: Record<string, "live" | "manual" | "unimplemented"> = {
  instagram: "live",
  facebook: "live",
  x: "live",
  youtube: "live",
  threads: "manual",
  tiktok: "unimplemented",
  linkedin: "unimplemented",
  kakao: "unimplemented",
}

function readinessTone(status: "ready" | "warning" | "blocked") {
  if (status === "ready") return "bg-emerald-50 text-emerald-700 border-emerald-200"
  if (status === "warning") return "bg-amber-50 text-amber-700 border-amber-200"
  return "bg-rose-50 text-rose-700 border-rose-200"
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
  if (status.includes("placeholder")) return "bg-orange-50 text-orange-700 border-orange-200"
  if (status.includes("manual") || status.includes("no_data")) return "bg-amber-50 text-amber-700 border-amber-200"
  if (status.includes("inactive")) return "bg-gray-100 text-gray-700 border-gray-200"
  if (status.includes("error")) return "bg-red-50 text-red-700 border-red-200"
  return "bg-gray-100 text-gray-700 border-gray-200"
}

function postSourceLabel(post: BenchmarkPostItem) {
  const source = String(post.raw_payload?.source || "")
  if (source === "youtube_api_live") return "실데이터"
  if (source === "x_api_live") return "실데이터"
  if (source === "instagram_business_discovery") return "실데이터"
  if (source === "facebook_page_posts") return "실데이터"
  if (source === "placeholder_benchmark_pipeline") return "샘플 대체"
  return "미상"
}

function postSourceTone(post: BenchmarkPostItem) {
  const source = String(post.raw_payload?.source || "")
  if (source === "placeholder_benchmark_pipeline") return "bg-orange-50 text-orange-700 border-orange-200"
  if (source) return "bg-green-50 text-green-700 border-green-200"
  return "bg-gray-100 text-gray-700 border-gray-200"
}

function postMetricLabel(post: BenchmarkPostItem) {
  const metric = String(post.raw_payload?.view_metric || "")
  if (metric === "actual") return "실조회수"
  if (metric === "proxy_from_public_metrics") return "프록시 조회수"
  if (metric === "proxy_from_like_comment") return "프록시 조회수"
  if (metric === "proxy_from_engagement") return "프록시 조회수"
  return "조회수"
}

export default function ClientBenchmarkPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [accounts, setAccounts] = useState<BenchmarkAccountItem[]>([])
  const [diagnostics, setDiagnostics] = useState<BenchmarkAccountDiagnosticItem[]>([])
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
      const [accountRows, diagnosticRows, topPostRows, profileRow] = await Promise.all([
        benchmarkingService.listAccounts(id),
        benchmarkingService.listAccountDiagnostics(id, currentPlatform),
        benchmarkingService.getTopPosts(id, currentPlatform, currentTopK),
        benchmarkingService.getActionProfile(id, currentPlatform),
      ])
      setAccounts(accountRows)
      setDiagnostics(diagnosticRows)
      setTopPosts(topPostRows)
      setProfile(profileRow)
    } finally {
      setLoading(false)
    }
  }, [id, platform, topK])

  useEffect(() => { void load() }, [load])
  useEffect(() => { void load(platform, topK) }, [load, platform, topK])

  const platformAccounts = useMemo(() => accounts.filter((item) => item.platform === platform), [accounts, platform])
  const diagnosticMap = useMemo(() => diagnostics.reduce<Record<string, BenchmarkAccountDiagnosticItem>>((acc, item) => {
    acc[item.account_id] = item
    return acc
  }, {}), [diagnostics])

  const platformSupportLevel = PLATFORM_SUPPORT_LEVEL[platform] || "unimplemented"
  const activePlatformAccounts = useMemo(() => platformAccounts.filter((item) => item.is_active), [platformAccounts])
  const topPostsSummary = useMemo(() => {
    const liveCount = topPosts.filter((post) => postSourceLabel(post) === "실데이터").length
    const placeholderCount = topPosts.filter((post) => postSourceLabel(post) === "샘플 대체").length
    const actualMetricCount = topPosts.filter((post) => String(post.raw_payload?.view_metric || "") === "actual").length
    const proxyMetricCount = topPosts.filter((post) => {
      const metric = String(post.raw_payload?.view_metric || "")
      return metric.startsWith("proxy_")
    }).length
    return {
      liveCount,
      placeholderCount,
      actualMetricCount,
      proxyMetricCount,
      total: topPosts.length,
    }
  }, [topPosts])

  const diagnosticSummary = useMemo(() => {
    const activeRows = diagnostics.filter((item) => item.is_active)
    return {
      blockedCount: activeRows.filter((item) => item.status === "manual_ingest_required").length,
      mixedCount: activeRows.filter((item) => item.status === "live_collected_mixed").length,
      noDataCount: activeRows.filter((item) => item.status === "no_data_collected").length,
      placeholderOnlyCount: activeRows.filter((item) => item.status === "placeholder_fallback").length,
      liveAccountCount: activeRows.filter((item) => item.status === "live_collected" || item.status === "live_collected_proxy_views").length,
      livePostCount: activeRows.reduce((sum, item) => sum + item.live_post_count, 0),
      placeholderPostCount: activeRows.reduce((sum, item) => sum + item.placeholder_post_count, 0),
      actualMetricCount: activeRows.reduce((sum, item) => sum + item.actual_metric_count, 0),
      proxyMetricCount: activeRows.reduce((sum, item) => sum + item.proxy_metric_count, 0),
      totalPostCount: activeRows.reduce((sum, item) => sum + item.total_post_count, 0),
      tokenMissingCount: activeRows.filter((item) => item.source_channel_connected && !item.source_channel_has_token).length,
      inactiveCount: diagnostics.filter((item) => !item.is_active).length,
    }
  }, [diagnostics])

  const readiness = useMemo(() => {
    if (platformAccounts.length === 0) {
      return {
        status: "blocked" as const,
        title: "계정 미등록",
        detail: "이 플랫폼의 벤치마킹 계정을 먼저 등록해야 현재 상태를 판단할 수 있습니다.",
      }
    }

    if (platformSupportLevel === "unimplemented") {
      return {
        status: "blocked" as const,
        title: "실수집기 미구현",
        detail: "현재 플랫폼은 운영 화면에서 준비 상태만 확인 가능하며 실벤치마킹 적재는 아직 지원되지 않습니다.",
      }
    }

    if (platformSupportLevel === "manual") {
      return {
        status: "warning" as const,
        title: "수동 확인 필요",
        detail: "자동 실수집이 아니라 운영자가 직접 수집/입력 여부를 확인해야 하는 플랫폼입니다.",
      }
    }

    if (diagnosticSummary.tokenMissingCount > 0) {
      return {
        status: "warning" as const,
        title: "토큰 누락 연결 있음",
        detail: `연결된 채널처럼 보이지만 access token이 없는 계정 ${diagnosticSummary.tokenMissingCount}개가 있습니다. 가짜 연동 상태를 먼저 정리해야 합니다.`,
      }
    }

    if (diagnosticSummary.mixedCount > 0) {
      return {
        status: "warning" as const,
        title: "실데이터/샘플 혼재",
        detail: `실데이터와 샘플 대체가 함께 있는 계정 ${diagnosticSummary.mixedCount}개가 있습니다. 운영 판단 시 분리해서 봐야 합니다.`,
      }
    }

    if (diagnosticSummary.liveAccountCount > 0) {
      return {
        status: "ready" as const,
        title: "직접 실데이터 확보",
        detail: diagnosticSummary.actualMetricCount > 0
          ? "현재 클라이언트 계정 기준 실조회수 데이터가 포함되어 있습니다."
          : "현재 클라이언트 계정 기준 실수집은 되었지만 조회수는 프록시 지표입니다.",
      }
    }

    if (diagnosticSummary.placeholderOnlyCount > 0) {
      return {
        status: "warning" as const,
        title: "샘플 대체만 존재",
        detail: `직접 실데이터 없이 placeholder fallback 계정 ${diagnosticSummary.placeholderOnlyCount}개가 남아 있습니다.`,
      }
    }

    if (diagnosticSummary.blockedCount > 0 || diagnosticSummary.noDataCount > 0) {
      return {
        status: "warning" as const,
        title: "직접 실데이터 없음",
        detail: `연결/collector 이슈 계정 ${diagnosticSummary.blockedCount}개, 아직 적재되지 않은 계정 ${diagnosticSummary.noDataCount}개가 있습니다.`,
      }
    }

    return {
      status: "warning" as const,
      title: "직접 실데이터 없음",
      detail: "계정은 등록되어 있지만 현재 클라이언트 기준 실수집 상태를 아직 확인하지 못했습니다. 연결 채널/토큰/collector 상태를 확인해야 합니다.",
    }
  }, [diagnosticSummary.actualMetricCount, diagnosticSummary.blockedCount, diagnosticSummary.liveAccountCount, diagnosticSummary.mixedCount, diagnosticSummary.noDataCount, diagnosticSummary.placeholderOnlyCount, diagnosticSummary.tokenMissingCount, platformAccounts.length, platformSupportLevel])

  const profileSummary = useMemo(() => {
    if (!profile) {
      return {
        title: "프로필 없음",
        detail: "아직 액션 랭귀지 프로필이 생성되지 않았습니다.",
      }
    }
    if (profile.source_scope === "industry_fallback") {
      return {
        title: "업종 fallback",
        detail: `${profile.industry_category || "미분류 업종"} 기준 샘플 ${profile.sample_count || 0}개로 생성된 공용 프로필입니다.`,
      }
    }
    return {
      title: "직접 학습",
      detail: `현재 클라이언트 데이터 ${profile.sample_count || 0}개 기준으로 생성된 직접 학습 프로필입니다.`,
    }
  }, [profile])

  async function handleCreateAccount() {
    if (!form.handle.trim()) return
    setSaving(true)
    try {
      await benchmarkingService.createAccount({
        client_id: id,
        platform,
        handle: form.handle.trim(),
        purpose: form.purpose,
        source_type: form.source_type,
        memo: form.memo.trim() || undefined,
        metadata_json: parseMetadata(platform, form.metadataInput),
      })
      setForm({ handle: "", purpose: "all", source_type: "manual", memo: "", metadataInput: "" })
      await load(platform, topK)
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
      await benchmarkingService.updateAccount(item.id, {
        handle: editForm.handle,
        purpose: editForm.purpose,
        source_type: editForm.source_type,
        memo: editForm.memo,
        is_active: editForm.is_active,
        metadata_json: parseMetadata(item.platform, editForm.metadataInput),
      })
      setEditingId(null)
      await load(platform, topK)
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(item: BenchmarkAccountItem) {
    await benchmarkingService.updateAccount(item.id, { is_active: !item.is_active })
    await load(platform, topK)
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

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">플랫폼 지원 상태</div>
          <div className="mt-2 text-sm font-semibold text-gray-900">{PLATFORM_SUPPORT[platform] || "미정"}</div>
          <div className="mt-2 text-xs text-gray-500">{platformSupportLevel === "live" ? "실수집 가능" : platformSupportLevel === "manual" ? "수동 확인 필요" : "아직 미구현"}</div>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">등록/활성 계정</div>
          <div className="mt-2 text-sm font-semibold text-gray-900">{platformAccounts.length}개 등록 · {activePlatformAccounts.length}개 활성</div>
          <div className="mt-2 text-xs text-gray-500">비활성 {Math.max(platformAccounts.length - activePlatformAccounts.length, 0)}개 · 토큰누락 {diagnosticSummary.tokenMissingCount}개</div>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">직접 실데이터 정합성</div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${readinessTone(readiness.status)}`}>{readiness.title}</span>
            {profile?.source_scope === "industry_fallback" && (
              <span className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-violet-50 text-violet-700 border-violet-200">Top Posts는 업종 fallback일 수 있음</span>
            )}
          </div>
          <div className="mt-2 text-xs text-gray-500">직접 실데이터 {diagnosticSummary.livePostCount} · 샘플대체 {diagnosticSummary.placeholderPostCount} · 미적재 {diagnosticSummary.noDataCount}</div>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">프로필 출처</div>
          <div className="mt-2 text-sm font-semibold text-gray-900">{profileSummary.title}</div>
          <div className="mt-2 text-xs text-gray-500">{profile ? `샘플 ${profile.sample_count || 0}개` : "프로필 미생성"}</div>
        </div>
      </div>

      <div className={`rounded-xl border px-4 py-3 text-xs ${readinessTone(readiness.status)}`}>
        <div className="font-semibold">현재 운영 판정: {readiness.title}</div>
        <div className="mt-1">{readiness.detail}</div>
        {profile?.source_scope === "industry_fallback" && topPostsSummary.total > 0 && (
          <div className="mt-1 text-[11px] opacity-80">현재 Top Posts는 이 클라이언트 직접 수집이 아니라 같은 업종 fallback 기준일 수 있습니다. 운영 판단은 위 직접 실데이터 정합성 카드와 계정 diagnostics를 우선 보셔야 합니다.</div>
        )}
        <div className="mt-1 text-[11px] opacity-80">{profileSummary.detail}</div>
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
                  const diagnostic = diagnosticMap[item.id]
                  const accountState = refreshState || diagnostic
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
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${item.is_active ? "bg-blue-50 text-blue-700 border-blue-200" : "bg-gray-100 text-gray-600 border-gray-200"}`}>{item.is_active ? "활성" : "비활성"}</span>
                            {diagnostic?.support_label && <span className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-slate-50 text-slate-700 border-slate-200">{diagnostic.support_label}</span>}
                            <button onClick={() => void toggleActive(item)} className="text-[11px] text-gray-600 underline underline-offset-2">{item.is_active ? "비활성화" : "재활성화"}</button>
                          </div>
                          {item.metadata_json && (
                            <div className="text-[11px] text-gray-500 break-all">metadata: {JSON.stringify(item.metadata_json)}</div>
                          )}
                          {item.memo && <div className="text-[11px] text-gray-500">memo: {item.memo}</div>}
                          {accountState && (
                            <div className="space-y-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <div className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${badgeTone(accountState.status)}`}>
                                  {accountState.status_label || accountState.status}
                                  {refreshState ? ` · ${refreshState.inserted > 0 ? `${refreshState.inserted}건 적재` : '적재 없음'}` : diagnostic ? ` · 실데이터 ${diagnostic.live_post_count} · 샘플 ${diagnostic.placeholder_post_count}` : ""}
                                </div>
                                {accountState.view_metric_label && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-sky-50 text-sky-700 border-sky-200">
                                    {accountState.view_metric_label}
                                  </div>
                                )}
                                {accountState.used_placeholder && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-orange-50 text-orange-700 border-orange-200">
                                    placeholder fallback
                                  </div>
                                )}
                                {diagnostic && !diagnostic.source_channel_has_token && diagnostic.source_channel_connected && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-rose-50 text-rose-700 border-rose-200">
                                    토큰 없음
                                  </div>
                                )}
                              </div>
                              {accountState.data_source_label && <div className="text-[11px] text-gray-600">데이터 소스: {accountState.data_source_label}</div>}
                              {accountState.source_channel_connected
                                ? <div className="text-[11px] text-emerald-700">연결 채널: {accountState.source_channel_account_name || accountState.source_channel_platform || item.platform}</div>
                                : <div className="text-[11px] text-amber-700">연결 상태: {accountState.source_channel_missing_reason || "연결 채널 확인 필요"}</div>}
                            </div>
                          )}
                          {accountState?.message && <div className="text-[11px] text-gray-600">{accountState.message}</div>}
                        </>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="bg-white rounded-xl border p-4 lg:col-span-2">
              <h2 className="font-semibold mb-3">액션 랭귀지 프로필</h2>
              <div className="mb-3 rounded-lg border bg-slate-50 px-3 py-2 text-xs text-slate-700">
                실데이터와 샘플 대체가 함께 있을 수 있습니다. 샘플 대체는 실제 벤치마킹 성과가 아니라 운영 화면 검증용 fallback입니다.
              </div>
              {!profile ? <div className="text-sm text-gray-400">아직 프로필이 없습니다.</div> : (
                <div className="space-y-4 text-sm">
                  <div className="flex flex-wrap gap-2">
                    <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${profile.source_scope === "industry_fallback" ? "bg-violet-50 text-violet-700 border-violet-200" : "bg-blue-50 text-blue-700 border-blue-200"}`}>
                      {profile.source_scope === "industry_fallback" ? "업종 fallback" : "직접 학습"}
                    </span>
                    {profile.industry_category && <span className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-emerald-50 text-emerald-700 border-emerald-200">업종 {profile.industry_category}</span>}
                    <span className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-gray-100 text-gray-700 border-gray-200">샘플 {profile.sample_count || 0}</span>
                  </div>
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
            {profile?.source_scope === "industry_fallback" && topPostsSummary.total > 0 && (
              <div className="mx-4 mt-4 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-xs text-violet-700">
                현재 Top Posts는 같은 업종의 기존 실데이터 fallback 결과일 수 있습니다. 이 클라이언트 직접 수집 성공 여부는 계정별 상태 배지와 직접 실데이터 정합성 카드로 판단해야 합니다.
              </div>
            )}
            <div className="divide-y">
              {topPosts.length === 0 ? <div className="p-4 text-sm text-gray-400">Top post 데이터가 없습니다.</div> : topPosts.map((post, index) => (
                <div key={post.id} className="p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-medium text-sm">#{index + 1} {post.hook_text || post.content_text?.slice(0, 60) || "제목 없음"}</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${postSourceTone(post)}`}>{postSourceLabel(post)}</span>
                        <span className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-sky-50 text-sky-700 border-sky-200">{postMetricLabel(post)}</span>
                      </div>
                      <div className="text-xs text-gray-500 mt-2">CTA: {post.cta_text || "없음"}</div>
                      {post.post_url && <a href={post.post_url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 mt-1 inline-block">원문 보기</a>}
                    </div>
                    <div className="text-right text-xs text-gray-500">
                      <div>{postMetricLabel(post)} {post.view_count.toLocaleString()}</div>
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
