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
  threads: "자동 실수집 미지원입니다. 현재는 운영자가 수동으로 수집/확인해야 합니다.",
  tiktok: "OAuth 연결은 있지만 벤치마킹 실수집기는 아직 없습니다.",
  linkedin: "OAuth 연결은 있지만 공개 벤치마킹 실수집기는 아직 없습니다.",
  kakao: "현재는 벤치마킹 실수집기 미구현입니다. 계정 등록은 가능하지만 준비 완료로 보면 안 됩니다.",
}

const PLATFORM_SUPPORT: Record<string, string> = {
  instagram: "실수집 지원 · 조회수 프록시",
  facebook: "실수집 지원 · 조회수 프록시",
  x: "실수집 지원 · 조회수 프록시",
  youtube: "실수집 지원 · 실조회수",
  threads: "수동 확인 전용",
  tiktok: "미구현 · 실수집기 없음",
  linkedin: "미구현 · 실수집기 없음",
  kakao: "미구현 · 실수집기 없음",
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
  if (status.includes("mixed")) return "bg-amber-50 text-amber-700 border-amber-200"
  if (status.includes("live_collected")) return "bg-green-50 text-green-700 border-green-200"
  if (status.includes("placeholder")) return "bg-orange-50 text-orange-700 border-orange-200"
  if (status.includes("manual") || status.includes("no_data")) return "bg-amber-50 text-amber-700 border-amber-200"
  if (status.includes("inactive")) return "bg-gray-100 text-gray-700 border-gray-200"
  if (status.includes("error")) return "bg-red-50 text-red-700 border-red-200"
  return "bg-gray-100 text-gray-700 border-gray-200"
}

function accountOperationalPriority(
  account: BenchmarkAccountItem,
  accountState?: RefreshAccountResult | BenchmarkAccountDiagnosticItem,
  latestRefreshAt?: string | null,
) {
  if (!account.is_active) return 90
  if (!accountState) return 70
  if (accountState.source_channel_connected && accountState.source_channel_has_token === false) return 0
  if (accountState.source_channel_duplicate_warning) return 5
  if (accountState.status === "collector_error") return 10
  if (accountState.status === "manual_ingest_required") return 15
  if (accountState.status === "no_data_collected") return 20
  if (!latestRefreshAt) return 30
  if (isStaleRefresh(latestRefreshAt)) return 35
  if (accountState.status === "live_collected_mixed") return 40
  if (accountState.status === "placeholder_fallback") return 50
  if (accountState.status === "live_collected" || accountState.status === "live_collected_proxy_views") return 80
  return 60
}

function formatDateTime(value?: string | null) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleString("ko-KR")
}

function parseTimestamp(value?: string | null) {
  if (!value) return null
  const date = new Date(value)
  const time = date.getTime()
  return Number.isNaN(time) ? null : time
}

function isStaleRefresh(value?: string | null, thresholdHours = 24) {
  const time = parseTimestamp(value)
  if (!time) return false
  return Date.now() - time >= thresholdHours * 60 * 60 * 1000
}

function optionalBoolean(value: boolean | null | undefined) {
  return typeof value === "boolean" ? value : undefined
}

function pickAccountState(
  refreshState?: RefreshAccountResult,
  diagnostic?: BenchmarkAccountDiagnosticItem,
) {
  if (!refreshState) return diagnostic
  if (!diagnostic) return refreshState

  const refreshTime = parseTimestamp(refreshState.refreshed_at)
  const diagnosticTime = parseTimestamp(diagnostic.last_refresh_at)

  if (refreshTime && diagnosticTime) {
    return refreshTime >= diagnosticTime ? refreshState : diagnostic
  }

  if (refreshTime) return refreshState
  if (diagnosticTime) return diagnostic
  return diagnostic
}

function postSourceLabel(post: BenchmarkPostItem) {
  const source = String(post.raw_payload?.source || "")
  if (source === "placeholder_benchmark_pipeline") return "샘플 대체"
  if (post.source_scope === "industry_fallback") return "실데이터 · 업종 fallback"
  if (source === "youtube_api_live") return "실데이터"
  if (source === "x_api_live") return "실데이터"
  if (source === "instagram_business_discovery") return "실데이터"
  if (source === "facebook_page_posts") return "실데이터"
  return post.source_scope_label || "미상"
}

function postSourceTone(post: BenchmarkPostItem) {
  const source = String(post.raw_payload?.source || "")
  if (source === "placeholder_benchmark_pipeline") return "bg-orange-50 text-orange-700 border-orange-200"
  if (post.source_scope === "industry_fallback") return "bg-violet-50 text-violet-700 border-violet-200"
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

function isCurrentClientPost(post: BenchmarkPostItem, clientId: string) {
  if (typeof post.is_direct_client_post === "boolean") return post.is_direct_client_post
  return String(post.client_id || "") === String(clientId)
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

  const load = useCallback(async (currentPlatform: string, currentTopK: number) => {
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
  }, [id])

  useEffect(() => {
    void load(platform, topK)
  }, [load, platform, topK])

  const platformAccounts = useMemo(() => accounts.filter((item) => item.platform === platform), [accounts, platform])
  const diagnosticMap = useMemo(() => diagnostics.reduce<Record<string, BenchmarkAccountDiagnosticItem>>((acc, item) => {
    acc[item.account_id] = item
    return acc
  }, {}), [diagnostics])
  const sortedPlatformAccounts = useMemo(() => {
    return [...platformAccounts].sort((a, b) => {
      const aRefresh = statusMap[a.id]
      const bRefresh = statusMap[b.id]
      const aDiagnostic = diagnosticMap[a.id]
      const bDiagnostic = diagnosticMap[b.id]
      const aState = pickAccountState(aRefresh, aDiagnostic)
      const bState = pickAccountState(bRefresh, bDiagnostic)
      const aRefreshTime = parseTimestamp(aRefresh?.refreshed_at)
      const bRefreshTime = parseTimestamp(bRefresh?.refreshed_at)
      const aDiagnosticTime = parseTimestamp(aDiagnostic?.last_refresh_at)
      const bDiagnosticTime = parseTimestamp(bDiagnostic?.last_refresh_at)
      const aUseRefreshMeta = Boolean(aRefresh && (!aDiagnosticTime || (aRefreshTime && aRefreshTime >= aDiagnosticTime)))
      const bUseRefreshMeta = Boolean(bRefresh && (!bDiagnosticTime || (bRefreshTime && bRefreshTime >= bDiagnosticTime)))
      const aLatestRefreshAt = aUseRefreshMeta ? (aRefresh?.refreshed_at || null) : (aDiagnostic?.last_refresh_at || null)
      const bLatestRefreshAt = bUseRefreshMeta ? (bRefresh?.refreshed_at || null) : (bDiagnostic?.last_refresh_at || null)
      const aPriority = accountOperationalPriority(a, aState, aLatestRefreshAt)
      const bPriority = accountOperationalPriority(b, bState, bLatestRefreshAt)
      if (aPriority !== bPriority) return aPriority - bPriority
      const aUpdated = parseTimestamp(a.updated_at)
      const bUpdated = parseTimestamp(b.updated_at)
      return (bUpdated || 0) - (aUpdated || 0)
    })
  }, [diagnosticMap, platformAccounts, statusMap])

  const platformSupportLevel = PLATFORM_SUPPORT_LEVEL[platform] || "unimplemented"
  const referenceOnlyPlatform = platformSupportLevel !== "live"
  const activePlatformAccounts = useMemo(() => platformAccounts.filter((item) => item.is_active), [platformAccounts])
  const topPostsSummary = useMemo(() => {
    const liveCount = topPosts.filter((post) => postSourceLabel(post) === "실데이터").length
    const placeholderCount = topPosts.filter((post) => postSourceLabel(post) === "샘플 대체").length
    const actualMetricCount = topPosts.filter((post) => String(post.raw_payload?.view_metric || "") === "actual").length
    const proxyMetricCount = topPosts.filter((post) => {
      const metric = String(post.raw_payload?.view_metric || "")
      return metric.startsWith("proxy_")
    }).length
    const directClientCount = topPosts.filter((post) => isCurrentClientPost(post, id)).length
    return {
      liveCount,
      placeholderCount,
      actualMetricCount,
      proxyMetricCount,
      directClientCount,
      fallbackClientCount: Math.max(topPosts.length - directClientCount, 0),
      total: topPosts.length,
    }
  }, [id, topPosts])

  const diagnosticSummary = useMemo(() => {
    const activeRows = diagnostics.filter((item) => item.is_active)
    const manualRequiredCount = activeRows.filter((item) => item.status === "manual_ingest_required").length
    const collectorErrorCount = activeRows.filter((item) => item.status === "collector_error").length
    const noDataCount = activeRows.filter((item) => item.status === "no_data_collected").length
    const tokenMissingRows = activeRows.filter((item) => item.source_channel_connected && item.source_channel_has_token === false)
    const tokenMissingCount = tokenMissingRows.length
    const duplicateConnectionAccountCount = activeRows.filter((item) => item.source_channel_duplicate_warning).length
    const duplicateConnectionCount = activeRows.reduce((sum, item) => sum + Math.max(item.source_channel_duplicate_count || 0, 0), 0)
    const lastRefreshProfileReadyCount = activeRows.filter((item) => Boolean(item.last_refresh_profile_generated || item.last_refresh_profile_id)).length
    const blockedAccountIds = new Set<string>([
      ...activeRows.filter((item) => item.status === "manual_ingest_required" || item.status === "collector_error").map((item) => item.account_id),
      ...tokenMissingRows.map((item) => item.account_id),
    ])
    const blockedOperationalIds = new Set<string>([
      ...blockedAccountIds,
      ...activeRows.filter((item) => item.status === "no_data_collected").map((item) => item.account_id),
    ])
    const blockedAccountCount = blockedAccountIds.size
    return {
      blockedAccountCount,
      manualRequiredCount,
      collectorErrorCount,
      mixedCount: activeRows.filter((item) => item.status === "live_collected_mixed").length,
      noDataCount,
      placeholderOnlyCount: activeRows.filter((item) => item.status === "placeholder_fallback").length,
      liveAccountCount: activeRows.filter((item) => item.status === "live_collected" || item.status === "live_collected_proxy_views").length,
      livePostCount: activeRows.reduce((sum, item) => sum + item.live_post_count, 0),
      placeholderPostCount: activeRows.reduce((sum, item) => sum + item.placeholder_post_count, 0),
      actualMetricCount: activeRows.reduce((sum, item) => sum + item.actual_metric_count, 0),
      proxyMetricCount: activeRows.reduce((sum, item) => sum + item.proxy_metric_count, 0),
      totalPostCount: activeRows.reduce((sum, item) => sum + item.total_post_count, 0),
      tokenMissingCount,
      duplicateConnectionAccountCount,
      duplicateConnectionCount,
      freshnessIssueCount: activeRows.filter((item) => !item.last_refresh_at || isStaleRefresh(item.last_refresh_at)).length,
      recentRefreshCount: activeRows.filter((item) => Boolean(item.last_refresh_at) && !isStaleRefresh(item.last_refresh_at)).length,
      lastRefreshProfileReadyCount,
      lastRefreshProfileMissingCount: Math.max(activeRows.length - lastRefreshProfileReadyCount, 0),
      blockedOperationalCount: blockedOperationalIds.size,
      neverRefreshedCount: activeRows.filter((item) => !item.last_refresh_at).length,
      staleRefreshCount: activeRows.filter((item) => Boolean(item.last_refresh_at) && isStaleRefresh(item.last_refresh_at)).length,
      inactiveCount: diagnostics.filter((item) => !item.is_active).length,
    }
  }, [diagnostics])

  const blockerAccounts = useMemo(() => {
    return sortedPlatformAccounts
      .map((account) => {
        const refreshState = statusMap[account.id]
        const diagnostic = diagnosticMap[account.id]
        const accountState = pickAccountState(refreshState, diagnostic)
        const refreshTime = parseTimestamp(refreshState?.refreshed_at)
        const diagnosticTime = parseTimestamp(diagnostic?.last_refresh_at)
        const useRefreshMeta = Boolean(refreshState && (!diagnosticTime || (refreshTime && refreshTime >= diagnosticTime)))
        const latestRefreshAt = useRefreshMeta ? (refreshState?.refreshed_at || null) : (diagnostic?.last_refresh_at || null)

        if (!account.is_active || !accountState) return null

        let priority = 0
        let reason = accountState.message || "운영 점검 필요"
        if (accountState.source_channel_connected && accountState.source_channel_has_token === false) {
          priority = 0
          reason = accountState.source_channel_missing_reason || "연결 레코드는 있으나 access token 없음"
        } else if (accountState.source_channel_duplicate_warning) {
          priority = 1
          reason = `동일 플랫폼 연결 ${accountState.source_channel_connection_count || (accountState.source_channel_duplicate_count || 0) + 1}개 중 사용 가능한 row 기준`
        } else if (accountState.status === "collector_error") {
          priority = 2
          reason = accountState.message || "최근 수집 오류 발생"
        } else if (accountState.status === "manual_ingest_required") {
          priority = 3
          reason = accountState.source_channel_missing_reason || accountState.message || "수동 확인 필요"
        } else if (accountState.status === "no_data_collected") {
          priority = 4
          reason = accountState.message || "실데이터 미적재"
        } else if (!latestRefreshAt) {
          priority = 5
          reason = "새로고침 이력 없음"
        } else if (isStaleRefresh(latestRefreshAt)) {
          priority = 6
          reason = "24시간 이상 지난 점검 상태"
        } else if (accountState.status === "live_collected_mixed") {
          priority = 7
          reason = "실데이터와 fallback이 함께 있어 분리 판단 필요"
        } else if (accountState.status === "placeholder_fallback") {
          priority = 8
          reason = "샘플 대체만 존재"
        } else {
          return null
        }

        return {
          id: account.id,
          handle: account.handle,
          status: accountState.status,
          statusLabel: accountState.status_label || accountState.status,
          reason,
          latestRefreshAt,
          priority,
        }
      })
      .filter((item): item is {
        id: string
        handle: string
        status: string
        statusLabel: string
        reason: string
        latestRefreshAt: string | null
        priority: number
      } => Boolean(item))
      .sort((a, b) => {
        if (a.priority !== b.priority) return a.priority - b.priority
        return (parseTimestamp(b.latestRefreshAt) || 0) - (parseTimestamp(a.latestRefreshAt) || 0)
      })
      .slice(0, 5)
  }, [diagnosticMap, sortedPlatformAccounts, statusMap])

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
        detail: "현재 플랫폼은 계정 등록/참고 메모는 가능하지만 실벤치마킹 적재는 아직 지원되지 않습니다. 화면에 참고용 데이터가 보여도 운영 준비 완료로 보면 안 됩니다.",
      }
    }

    if (platformSupportLevel === "manual") {
      return {
        status: "warning" as const,
        title: "수동 확인 필요",
        detail: "자동 실수집이 아니라 운영자가 직접 수집/입력 여부를 확인해야 하는 플랫폼입니다. 참고용 데이터가 보이더라도 자동 실데이터 준비 상태를 뜻하지 않습니다.",
      }
    }

    if (diagnosticSummary.tokenMissingCount > 0) {
      return {
        status: "warning" as const,
        title: "토큰 누락 연결 있음",
        detail: `연결된 채널처럼 보이지만 access token이 없는 계정 ${diagnosticSummary.tokenMissingCount}개가 있습니다. 가짜 연동 상태를 먼저 정리해야 합니다.`,
      }
    }

    if (diagnosticSummary.duplicateConnectionAccountCount > 0) {
      return {
        status: "warning" as const,
        title: "중복 연결 정리 필요",
        detail: `동일 플랫폼 연결이 중복된 계정 ${diagnosticSummary.duplicateConnectionAccountCount}개, 중복 row ${diagnosticSummary.duplicateConnectionCount}개가 있습니다. 어떤 row 기준으로 실수집하는지 운영자가 혼동할 수 있습니다.`,
      }
    }

    if (diagnosticSummary.collectorErrorCount > 0) {
      return {
        status: "warning" as const,
        title: "최근 수집 오류 발생",
        detail: `최근 새로고침 기준 collector 오류 계정 ${diagnosticSummary.collectorErrorCount}개가 있습니다. 실데이터 없음과 구분해서 먼저 원인 확인이 필요합니다.`,
      }
    }

    if (diagnosticSummary.neverRefreshedCount > 0 || diagnosticSummary.staleRefreshCount > 0) {
      return {
        status: "warning" as const,
        title: "점검 이력 부족",
        detail: `새로고침 이력이 없는 계정 ${diagnosticSummary.neverRefreshedCount}개, 24시간 이상 지난 계정 ${diagnosticSummary.staleRefreshCount}개가 있습니다. 현재 상태를 최신 운영 정보로 보기 어렵습니다.`,
      }
    }

    if (diagnosticSummary.mixedCount > 0) {
      return {
        status: "warning" as const,
        title: "실데이터/샘플 혼재",
        detail: `실데이터와 샘플 대체가 함께 있는 계정 ${diagnosticSummary.mixedCount}개가 있습니다. 운영 판단 시 분리해서 봐야 합니다.`,
      }
    }

    if (diagnosticSummary.liveAccountCount > 0 && (diagnosticSummary.placeholderOnlyCount > 0 || diagnosticSummary.blockedAccountCount > 0 || diagnosticSummary.noDataCount > 0)) {
      return {
        status: "warning" as const,
        title: "부분 실데이터 확보",
        detail: `실데이터 계정 ${diagnosticSummary.liveAccountCount}개가 있어도 샘플 대체 ${diagnosticSummary.placeholderOnlyCount}개, 연결/collector 차단 계정 ${diagnosticSummary.blockedAccountCount}개, 미적재 ${diagnosticSummary.noDataCount}개가 함께 남아 있습니다. 현재 플랫폼 전체를 ready로 보면 안 됩니다.`,
      }
    }

    if (diagnosticSummary.placeholderOnlyCount > 0) {
      return {
        status: "warning" as const,
        title: "샘플 대체만 존재",
        detail: `직접 실데이터 없이 placeholder fallback 계정 ${diagnosticSummary.placeholderOnlyCount}개가 남아 있습니다.`,
      }
    }

    if (diagnosticSummary.blockedAccountCount > 0 || diagnosticSummary.noDataCount > 0) {
      return {
        status: "warning" as const,
        title: "직접 실데이터 없음",
        detail: `연결/collector 차단 계정 ${diagnosticSummary.blockedAccountCount}개, 아직 적재되지 않은 계정 ${diagnosticSummary.noDataCount}개가 있습니다.`,
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

    return {
      status: "warning" as const,
      title: "직접 실데이터 없음",
      detail: "계정은 등록되어 있지만 현재 클라이언트 기준 실수집 상태를 아직 확인하지 못했습니다. 연결 채널/토큰/collector 상태를 확인해야 합니다.",
    }
  }, [diagnosticSummary.actualMetricCount, diagnosticSummary.blockedAccountCount, diagnosticSummary.collectorErrorCount, diagnosticSummary.duplicateConnectionAccountCount, diagnosticSummary.duplicateConnectionCount, diagnosticSummary.liveAccountCount, diagnosticSummary.mixedCount, diagnosticSummary.neverRefreshedCount, diagnosticSummary.noDataCount, diagnosticSummary.placeholderOnlyCount, diagnosticSummary.staleRefreshCount, diagnosticSummary.tokenMissingCount, platformAccounts.length, platformSupportLevel])

  const profileSummary = useMemo(() => {
    if (!profile) {
      return {
        title: referenceOnlyPlatform ? "참고 프로필 없음" : "프로필 없음",
        detail: referenceOnlyPlatform
          ? "이 플랫폼은 자동 실수집 대상이 아니므로 프로필이 보이지 않아도 운영 blocker가 아닙니다. 실연동/수동 수집 여부를 먼저 확인해야 합니다."
          : "아직 액션 랭귀지 프로필이 생성되지 않았습니다.",
      }
    }
    if (profile.source_scope === "industry_fallback") {
      return {
        title: referenceOnlyPlatform ? "업종 fallback 참고자료" : "업종 fallback",
        detail: `${profile.industry_category || "미분류 업종"} 기준 샘플 ${profile.sample_count || 0}개로 생성된 공용 프로필입니다.${referenceOnlyPlatform ? " 자동 실수집 준비 완료를 뜻하지 않고 참고자료로만 봐야 합니다." : ""}`,
      }
    }
    return {
      title: referenceOnlyPlatform ? "직접 학습 참고자료" : "직접 학습",
      detail: `현재 클라이언트 데이터 ${profile.sample_count || 0}개 기준으로 생성된 직접 학습 프로필입니다.${referenceOnlyPlatform ? " 다만 이 플랫폼은 자동 실수집 readiness 근거가 아니라 참고자료로만 해석해야 합니다." : ""}`,
    }
  }, [profile, referenceOnlyPlatform])

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
          <div className="mt-2 text-xs text-gray-500">비활성 {Math.max(platformAccounts.length - activePlatformAccounts.length, 0)}개 · 토큰누락 {diagnosticSummary.tokenMissingCount}개 · 중복연결 {diagnosticSummary.duplicateConnectionAccountCount}계정/{diagnosticSummary.duplicateConnectionCount}row · 수집오류 {diagnosticSummary.collectorErrorCount}개</div>
          <div className="mt-1 text-xs text-gray-500">새로고침 없음 {diagnosticSummary.neverRefreshedCount}개 · 24시간 초과 {diagnosticSummary.staleRefreshCount}개</div>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">직접 실데이터 정합성</div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${readinessTone(readiness.status)}`}>{readiness.title}</span>
            {profile?.source_scope === "industry_fallback" && (
              <span className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-violet-50 text-violet-700 border-violet-200">Top Posts는 업종 fallback일 수 있음</span>
            )}
          </div>
          <div className="mt-2 text-xs text-gray-500">실데이터 계정 {diagnosticSummary.liveAccountCount} · 혼재 {diagnosticSummary.mixedCount} · 샘플대체 {diagnosticSummary.placeholderOnlyCount} · 운영 blocker(중복제외) {diagnosticSummary.blockedOperationalCount}</div>
          <div className="mt-1 text-xs text-gray-500">실데이터 포스트 {diagnosticSummary.livePostCount} · 샘플 포스트 {diagnosticSummary.placeholderPostCount} · 실조회수 {diagnosticSummary.actualMetricCount} · 프록시조회수 {diagnosticSummary.proxyMetricCount}</div>
          <div className="mt-1 text-xs text-gray-500">현재 Top Posts 기준 직접클라이언트 {topPostsSummary.directClientCount} · 업종 fallback {topPostsSummary.fallbackClientCount}</div>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">프로필 출처</div>
          <div className="mt-2 text-sm font-semibold text-gray-900">{profileSummary.title}</div>
          <div className="mt-2 text-xs text-gray-500">{profile ? `샘플 ${profile.sample_count || 0}개` : "프로필 미생성"}</div>
          <div className="mt-1 text-xs text-gray-500">최근 점검 {diagnosticSummary.recentRefreshCount}개 · 점검 필요 {diagnosticSummary.freshnessIssueCount}개 · 프로필 생성됨 {diagnosticSummary.lastRefreshProfileReadyCount}개</div>
        </div>
      </div>

      <div className={`rounded-xl border px-4 py-3 text-xs ${readinessTone(readiness.status)}`}>
        <div className="font-semibold">현재 운영 판정: {readiness.title}</div>
        <div className="mt-1">{readiness.detail}</div>
        {referenceOnlyPlatform && (
          <div className="mt-1 text-[11px] opacity-80">이 플랫폼은 자동 실수집 readiness 대상이 아닙니다. 아래 Top Posts/프로필이 보여도 운영 참고자료로만 해석해야 합니다.</div>
        )}
        {profile?.source_scope === "industry_fallback" && topPostsSummary.total > 0 && (
          <div className="mt-1 text-[11px] opacity-80">현재 Top Posts는 이 클라이언트 직접 수집이 아니라 같은 업종 fallback 기준일 수 있습니다. 운영 판단은 위 직접 실데이터 정합성 카드와 계정 diagnostics를 우선 보셔야 합니다.</div>
        )}
        <div className="mt-1 text-[11px] opacity-80">{profileSummary.detail}</div>
      </div>

      {blockerAccounts.length > 0 && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-900">
          <div className="font-semibold">즉시 확인 필요 계정</div>
          <div className="mt-1 text-[11px] text-rose-800">운영 blocker 우선순위 기준 상위 5개만 노출합니다. 토큰 없음/중복 연결/수집 오류를 먼저 정리하셔야 현재 상태를 정직하게 볼 수 있습니다.</div>
          <div className="mt-3 space-y-2">
            {blockerAccounts.map((item) => (
              <div key={item.id} className="rounded-lg border border-rose-100 bg-white/80 px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-rose-900">{item.handle}</span>
                  <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${badgeTone(item.status)}`}>{item.statusLabel}</span>
                  {item.latestRefreshAt ? (
                    <span className="text-[11px] text-rose-700">마지막 점검 {formatDateTime(item.latestRefreshAt) || item.latestRefreshAt}</span>
                  ) : (
                    <span className="text-[11px] text-rose-700">새로고침 이력 없음</span>
                  )}
                </div>
                <div className="mt-1 text-[11px] text-rose-800">{item.reason}</div>
              </div>
            ))}
          </div>
        </div>
      )}

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
              <div className="mb-3 rounded-lg border bg-amber-50 px-3 py-2 text-[11px] text-amber-800">
                운영 blocker 우선순위로 정렬했습니다: 토큰 없음 → 중복 연결 → 수집 오류 → 수동 확인/미적재 → 점검 이력 부족 → 혼재/샘플 대체 → 실데이터 확보 → 비활성.
              </div>
              <div className="space-y-3 text-sm">
                {sortedPlatformAccounts.length === 0 ? <div className="text-gray-400">등록된 계정 없음</div> : sortedPlatformAccounts.map((item) => {
                  const refreshState = statusMap[item.id]
                  const diagnostic = diagnosticMap[item.id]
                  const accountState = pickAccountState(refreshState, diagnostic)
                  const refreshTime = parseTimestamp(refreshState?.refreshed_at)
                  const diagnosticTime = parseTimestamp(diagnostic?.last_refresh_at)
                  const useRefreshMeta = Boolean(refreshState && (!diagnosticTime || (refreshTime && refreshTime >= diagnosticTime)))
                  const latestRefreshAt = useRefreshMeta ? (refreshState?.refreshed_at || null) : (diagnostic?.last_refresh_at || null)
                  const latestRefreshStatus = useRefreshMeta ? (refreshState?.status || null) : (diagnostic?.last_refresh_status || null)
                  const latestRefreshStatusLabel = useRefreshMeta ? (refreshState?.status_label || null) : (diagnostic?.last_refresh_status_label || null)
                  const latestRefreshMessage = useRefreshMeta ? (refreshState?.message || null) : (diagnostic?.last_refresh_message || null)
                  const latestRefreshInserted = useRefreshMeta ? (refreshState?.inserted ?? 0) : (diagnostic?.last_refresh_inserted ?? 0)
                  const latestRefreshDataSourceLabel = useRefreshMeta ? (refreshState?.data_source_label || null) : (diagnostic?.last_refresh_data_source_label || null)
                  const latestRefreshViewMetricLabel = useRefreshMeta ? (refreshState?.view_metric_label || null) : (diagnostic?.last_refresh_view_metric_label || null)
                  const latestRefreshUsedPlaceholder = useRefreshMeta ? Boolean(refreshState?.used_placeholder) : Boolean(diagnostic?.last_refresh_used_placeholder)
                  const latestRefreshSourceConnected = useRefreshMeta
                    ? optionalBoolean(refreshState?.source_channel_connected)
                    : optionalBoolean(diagnostic?.last_refresh_source_channel_connected)
                  const latestRefreshSourcePlatform = useRefreshMeta ? (refreshState?.source_channel_platform || null) : (diagnostic?.last_refresh_source_channel_platform || null)
                  const latestRefreshSourceAccountName = useRefreshMeta ? (refreshState?.source_channel_account_name || null) : (diagnostic?.last_refresh_source_channel_account_name || null)
                  const latestRefreshSourceMissingReason = useRefreshMeta ? (refreshState?.source_channel_missing_reason || null) : (diagnostic?.last_refresh_source_channel_missing_reason || null)
                  const latestRefreshSourceHasToken = useRefreshMeta
                    ? optionalBoolean(refreshState?.source_channel_has_token)
                    : optionalBoolean(diagnostic?.last_refresh_source_channel_has_token)
                  const latestRefreshSourceConnectionCount = useRefreshMeta ? Number(refreshState?.source_channel_connection_count || 0) : Number(diagnostic?.last_refresh_source_channel_connection_count || 0)
                  const latestRefreshSourceDuplicateCount = useRefreshMeta ? Number(refreshState?.source_channel_duplicate_count || 0) : Number(diagnostic?.last_refresh_source_channel_duplicate_count || 0)
                  const latestRefreshSourceDuplicateWarning = useRefreshMeta ? Boolean(refreshState?.source_channel_duplicate_warning) : Boolean(diagnostic?.last_refresh_source_channel_duplicate_warning)
                  const latestProfileGenerated = useRefreshMeta
                    ? Boolean(refreshState?.profile_generated || refreshState?.profile_id)
                    : Boolean(diagnostic?.last_refresh_profile_generated || diagnostic?.last_refresh_profile_id)
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
                                  {latestRefreshAt
                                    ? ` · ${latestRefreshInserted > 0 ? `${latestRefreshInserted}건 적재` : '적재 없음'}`
                                    : diagnostic
                                      ? ` · 실데이터 ${diagnostic.live_post_count} · 샘플 ${diagnostic.placeholder_post_count}`
                                      : ""}
                                </div>
                                {accountState.view_metric_label && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-sky-50 text-sky-700 border-sky-200">
                                    {accountState.view_metric_label}
                                  </div>
                                )}
                                {(accountState.used_placeholder || latestRefreshUsedPlaceholder) && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-orange-50 text-orange-700 border-orange-200">
                                    placeholder fallback
                                  </div>
                                )}
                                {latestRefreshStatusLabel && (
                                  <div className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${badgeTone(latestRefreshStatus || undefined)}`}>
                                    마지막 점검 {latestRefreshStatusLabel}
                                  </div>
                                )}
                                {latestRefreshAt && (
                                  <div className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${latestProfileGenerated ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-slate-100 text-slate-700 border-slate-200"}`}>
                                    {latestProfileGenerated ? "프로필 생성됨" : "프로필 미생성"}
                                  </div>
                                )}
                                {!latestRefreshAt && item.is_active && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-amber-50 text-amber-700 border-amber-200">
                                    새로고침 이력 없음
                                  </div>
                                )}
                                {latestRefreshAt && isStaleRefresh(latestRefreshAt) && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-amber-50 text-amber-700 border-amber-200">
                                    24시간 이상 경과
                                  </div>
                                )}
                                {latestRefreshAt && latestRefreshSourceConnected === true && latestRefreshSourceHasToken === undefined && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-slate-100 text-slate-700 border-slate-200">
                                    마지막 점검 토큰상태 미확인
                                  </div>
                                )}
                                {accountState.source_channel_connected && accountState.source_channel_has_token === undefined && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-slate-100 text-slate-700 border-slate-200">
                                    토큰상태 미확인
                                  </div>
                                )}
                                {accountState.source_channel_connected && accountState.source_channel_has_token === false && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-rose-50 text-rose-700 border-rose-200">
                                    토큰 없음
                                  </div>
                                )}
                                {accountState.source_channel_duplicate_warning && (
                                  <div className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-violet-50 text-violet-700 border-violet-200">
                                    중복 연결 {accountState.source_channel_connection_count || (accountState.source_channel_duplicate_count || 0) + 1}개
                                  </div>
                                )}
                              </div>
                              {(accountState.data_source_label || latestRefreshDataSourceLabel) && <div className="text-[11px] text-gray-600">데이터 소스: {accountState.data_source_label || latestRefreshDataSourceLabel}</div>}
                              {!accountState.view_metric_label && latestRefreshViewMetricLabel && <div className="text-[11px] text-gray-600">최근 측정 기준: {latestRefreshViewMetricLabel}</div>}
                              {accountState.source_channel_connected ? (
                                <div className={`text-[11px] ${accountState.source_channel_has_token === false ? "text-amber-700" : accountState.source_channel_has_token === true ? "text-emerald-700" : "text-slate-500"}`}>
                                  연결 채널: {accountState.source_channel_account_name || accountState.source_channel_platform || item.platform}
                                  {accountState.source_channel_has_token === false ? ` · ${accountState.source_channel_missing_reason || "토큰 없음"}` : accountState.source_channel_has_token === undefined ? " · 토큰 상태 미확인" : ""}
                                  {accountState.source_channel_duplicate_warning ? ` · 동일 플랫폼 연결 ${accountState.source_channel_connection_count || (accountState.source_channel_duplicate_count || 0) + 1}개 중 사용 가능한 row 기준` : ""}
                                </div>
                              ) : (
                                <div className="text-[11px] text-amber-700">연결 상태: {accountState.source_channel_missing_reason || "연결 채널 확인 필요"}</div>
                              )}
                              {latestRefreshAt && latestRefreshSourceConnected === true && (
                                <div className={`text-[11px] ${latestRefreshSourceHasToken === false ? "text-amber-700" : latestRefreshSourceHasToken === true ? "text-slate-600" : "text-slate-500"}`}>
                                  마지막 점검 기준 연결 채널: {latestRefreshSourceAccountName || latestRefreshSourcePlatform || item.platform}
                                  {latestRefreshSourceHasToken === false ? ` · ${latestRefreshSourceMissingReason || "토큰 없음"}` : latestRefreshSourceHasToken === undefined ? " · 토큰 상태 미확인" : ""}
                                  {latestRefreshSourceDuplicateWarning ? ` · 동일 플랫폼 연결 ${latestRefreshSourceConnectionCount || latestRefreshSourceDuplicateCount + 1}개 중 사용 가능한 row 기준` : ""}
                                </div>
                              )}
                              {latestRefreshAt && latestRefreshSourceConnected === false && latestRefreshSourceMissingReason && (
                                <div className="text-[11px] text-amber-700">마지막 점검 기준 연결 상태: {latestRefreshSourceMissingReason}</div>
                              )}
                              {latestRefreshAt && (
                                <div className="text-[11px] text-gray-500">마지막 새로고침: {formatDateTime(latestRefreshAt) || latestRefreshAt}</div>
                              )}
                            </div>
                          )}
                          {accountState?.message && <div className="text-[11px] text-gray-600">{accountState.message}</div>}
                          {!refreshState && latestRefreshMessage && latestRefreshStatus === "collector_error" && (
                            <div className="text-[11px] text-red-700">최근 수집 오류: {latestRefreshMessage}</div>
                          )}
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
                {referenceOnlyPlatform ? " 현재 플랫폼은 자동 실수집 readiness 대상이 아니므로, 프로필이 보이더라도 참고자료로만 해석해야 합니다." : ""}
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
            {((profile?.source_scope === "industry_fallback" || topPostsSummary.fallbackClientCount > 0) || referenceOnlyPlatform) && topPostsSummary.total > 0 && (
              <div className={`mx-4 mt-4 rounded-lg border px-3 py-2 text-xs ${referenceOnlyPlatform ? "border-amber-200 bg-amber-50 text-amber-800" : "border-violet-200 bg-violet-50 text-violet-700"}`}>
                {referenceOnlyPlatform
                  ? `현재 플랫폼은 자동 실수집 readiness 대상이 아닙니다. Top Posts ${topPostsSummary.total}개는 운영 참고자료일 뿐이며, 직접 실데이터 성공 판정으로 보면 안 됩니다.`
                  : `현재 Top Posts ${topPostsSummary.total}개 중 직접클라이언트 ${topPostsSummary.directClientCount}개, 업종 fallback ${topPostsSummary.fallbackClientCount}개입니다. 이 클라이언트 직접 수집 성공 여부는 계정별 상태 배지와 직접 실데이터 정합성 카드로 판단해야 합니다.`}
              </div>
            )}
            <div className="divide-y">
              {topPosts.length === 0 ? (
                <div className="p-4 text-sm text-gray-400">
                  Top post 데이터가 없습니다.
                  {diagnosticSummary.placeholderPostCount > 0 && (
                    <div className="mt-2 text-xs text-amber-700">
                      기존 placeholder 포스트는 직접 실데이터나 업종 fallback 근거로 쓰지 않도록 Top Posts/프로필 계산에서 제외했습니다.
                    </div>
                  )}
                </div>
              ) : topPosts.map((post, index) => (
                <div key={post.id} className="p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-medium text-sm">#{index + 1} {post.hook_text || post.content_text?.slice(0, 60) || "제목 없음"}</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${postSourceTone(post)}`}>{postSourceLabel(post)}</span>
                        <span className="inline-flex items-center rounded-full border px-2 py-1 text-[11px] bg-sky-50 text-sky-700 border-sky-200">{postMetricLabel(post)}</span>
                        <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] ${isCurrentClientPost(post, id) ? "bg-blue-50 text-blue-700 border-blue-200" : "bg-violet-50 text-violet-700 border-violet-200"}`}>
                          {post.source_scope_label || (isCurrentClientPost(post, id) ? "직접 클라이언트" : "업종 fallback")}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 mt-2">CTA: {post.cta_text || "없음"}</div>
                      {!isCurrentClientPost(post, id) && (
                        <div className="text-[11px] text-violet-700 mt-1">현재 클라이언트 직접 수집 포스트가 아니라 같은 업종 다른 클라이언트에서 가져온 fallback입니다.</div>
                      )}
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
