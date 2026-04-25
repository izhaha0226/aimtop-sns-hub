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
    token_missing: number
  }
  items: Array<{
    id: string
    platform: string
    account_name?: string
    health: "healthy" | "expiring" | "reauth_required" | "unknown" | "token_missing"
    token_expires_at?: string | null
    has_access_token?: boolean
    health_label?: string | null
  }>
}

type PipelineKey = "ai_generation" | "oauth_connections" | "publishing" | "benchmarking" | "unknown"

interface PipelineReadiness {
  summary: {
    ready: number
    warning: number
    blocked: number
  }
  items: Array<{
    key: PipelineKey | string
    label: string
    status: "ready" | "warning" | "blocked"
    summary: string
    details: Record<string, string | number | boolean | null>
  }>
}

interface PublishObservability {
  summary: {
    connected_channels: number
    healthy_channels: number
    supported_connected_channels: number
    supported_healthy_channels: number
    unsupported_connected_channels: number
    reauth_required_channels: number
    token_missing_channels: number
    unknown_token_channels: number
    published_with_evidence: number
    published_without_evidence: number
    failed_with_error: number
    failed_without_error: number
    failed_with_stale_evidence: number
    failed_missing_evidence: number
    failed_unsupported_platform: number
    failed_token_expired: number
    failed_token_missing: number
    failed_missing_channel: number
    failed_retrying: number
    retry_pending_schedules: number
    retry_pending_token_missing: number
    retry_pending_token_expired: number
    retry_pending_missing_channel: number
    retry_pending_unsupported_platform: number
    retry_pending_other: number
    failed_other: number
  }
  published_items: Array<{
    id: string
    title: string
    platform_post_id?: string | null
    published_url?: string | null
    published_at?: string | null
    channel_connection_id?: string | null
    channel_type?: string | null
    account_name?: string | null
  }>
  suspicious_items: Array<{
    id: string
    title: string
    published_at?: string | null
    updated_at?: string | null
    schedule_status?: string | null
    schedule_retry_count?: number
    schedule_error_message?: string | null
    schedule_scheduled_at?: string | null
    failure_category?: string | null
    failure_label?: string | null
    channel_connection_id?: string | null
    channel_type?: string | null
    account_name?: string | null
  }>
  stale_evidence_items: Array<{
    id: string
    title: string
    platform_post_id?: string | null
    published_url?: string | null
    published_at?: string | null
    publish_error?: string | null
    failure_category?: string | null
    failure_label?: string | null
    updated_at?: string | null
    channel_connection_id?: string | null
    channel_type?: string | null
    account_name?: string | null
  }>
  failed_items: Array<{
    id: string
    title: string
    publish_error?: string | null
    failure_category?: string | null
    failure_label?: string | null
    updated_at?: string | null
    schedule_status?: string | null
    schedule_retry_count?: number
    schedule_error_message?: string | null
    schedule_scheduled_at?: string | null
    channel_connection_id?: string | null
    channel_type?: string | null
    account_name?: string | null
  }>
  retry_pending_items: Array<{
    schedule_id: string
    content_id: string
    title: string
    retry_count?: number
    scheduled_at?: string | null
    updated_at?: string | null
    error_message?: string | null
    failure_category?: string | null
    failure_label?: string | null
    channel_connection_id?: string | null
    channel_type?: string | null
    account_name?: string | null
  }>
}

const EMPTY_CHANNELS_HEALTH: ChannelsHealth = {
  summary: { healthy: 0, expiring: 0, reauth_required: 0, unknown: 0, token_missing: 0 },
  items: [],
}

const EMPTY_PIPELINE_READINESS: PipelineReadiness = {
  summary: { ready: 0, warning: 0, blocked: 0 },
  items: [],
}

const EMPTY_PUBLISH_OBSERVABILITY: PublishObservability = {
  summary: {
    connected_channels: 0,
    healthy_channels: 0,
    supported_connected_channels: 0,
    supported_healthy_channels: 0,
    unsupported_connected_channels: 0,
    reauth_required_channels: 0,
    token_missing_channels: 0,
    unknown_token_channels: 0,
    published_with_evidence: 0,
    published_without_evidence: 0,
    failed_with_error: 0,
    failed_without_error: 0,
    failed_with_stale_evidence: 0,
    failed_missing_evidence: 0,
    failed_unsupported_platform: 0,
    failed_token_expired: 0,
    failed_token_missing: 0,
    failed_missing_channel: 0,
    failed_retrying: 0,
    retry_pending_schedules: 0,
    retry_pending_token_missing: 0,
    retry_pending_token_expired: 0,
    retry_pending_missing_channel: 0,
    retry_pending_unsupported_platform: 0,
    retry_pending_other: 0,
    failed_other: 0,
  },
  published_items: [],
  suspicious_items: [],
  stale_evidence_items: [],
  failed_items: [],
  retry_pending_items: [],
}

const PIPELINE_DETAIL_LABELS: Record<string, string> = {
  active_task_policies: "활성 정책",
  blocked_tasks: "막힌 정책",
  fallback_only_tasks: "fallback 전용",
  fallback_missing_tasks: "fallback 누락",
  missing_provider_config_tasks: "설정 누락",
  inactive_provider_tasks: "비활성 정책",
  primary_ready_tasks: "기본 경로 가능",
  fallback_ready_tasks: "fallback 가능",
  openai_key_present: "OpenAI 키",
  claude_cli_available: "Claude CLI",
  primary_routes: "기본 경로",
  fallback_routes: "Fallback 경로",
  meta_app_id_present: "Meta App ID",
  meta_app_secret_present: "Meta App Secret",
  connected_channels: "연결 채널",
  healthy_channels: "건강한 전체 채널",
  reauth_required: "재인증 필요",
  token_missing_channels: "토큰 없음 채널",
  supported_connected_channels: "지원 채널",
  supported_healthy_channels: "건강한 지원 채널",
  unsupported_connected_channels: "미지원 연결 채널",
  unknown_token_channels: "토큰 상태 미확인",
  published_evidence_count: "발행 증거 수",
  suspicious_published_without_evidence: "증거 없는 published",
  failed_publish_count: "발행 실패",
  failed_without_error: "실패 · 사유 미기록",
  failed_with_stale_evidence: "실패인데 증거 남음",
  failed_token_missing: "실패 · 토큰 없음",
  failed_token_expired: "실패 · 토큰 만료",
  failed_missing_channel: "실패 · 채널/콘텐츠 누락",
  failed_unsupported_platform: "실패 · 미지원 채널",
  failed_missing_evidence: "실패 · 증거 누락",
  failed_retrying: "실패 · 재시도 중",
  failed_other: "실패 · 기타",
  retry_pending_schedules: "재시도 대기 예약",
  retry_pending_token_missing: "재시도 · 토큰 없음",
  retry_pending_token_expired: "재시도 · 토큰 만료",
  retry_pending_missing_channel: "재시도 · 채널 누락",
  retry_pending_unsupported_platform: "재시도 · 미지원 채널",
  retry_pending_other: "재시도 · 기타",
  active_accounts: "활성 계정",
  live_supported_accounts: "실수집 지원 계정",
  usable_live_supported_accounts: "토큰 갖춘 실수집 가능 계정",
  live_accounts: "실데이터 계정",
  mixed_accounts: "혼재 계정",
  placeholder_only_accounts: "샘플 대체 전용",
  no_data_accounts: "실데이터 없음",
  token_missing_accounts: "토큰 누락",
  collector_error_accounts: "수집 오류",
  manual_required_accounts: "수동 필요",
  manual_supported_accounts: "수동 지원 플랫폼",
  unimplemented_accounts: "미구현 플랫폼",
  duplicate_source_accounts: "중복 연결 계정",
  duplicate_source_connections: "중복 연결 수",
  never_refreshed_accounts: "새로고침 없음",
  stale_refresh_accounts: "24시간 초과",
  inactive_accounts: "비활성 계정",
  live_post_count: "실데이터 포스트",
  placeholder_post_count: "샘플 포스트",
  actual_metric_posts: "실조회수 포스트",
  proxy_metric_posts: "프록시조회수 포스트",
  benchmark_accounts: "벤치 계정 수",
  benchmark_posts: "벤치 포스트 수",
}

const PIPELINE_DETAIL_ORDER: Record<PipelineKey, string[]> = {
  ai_generation: ["blocked_tasks", "fallback_only_tasks", "fallback_missing_tasks", "primary_ready_tasks", "openai_key_present", "claude_cli_available"],
  oauth_connections: [
    "reauth_required",
    "token_missing_channels",
    "unknown_token_channels",
    "connected_channels",
    "supported_connected_channels",
    "healthy_channels",
    "supported_healthy_channels",
    "unsupported_connected_channels",
    "meta_app_id_present",
    "meta_app_secret_present",
  ],
  publishing: [
    "suspicious_published_without_evidence",
    "failed_with_stale_evidence",
    "failed_publish_count",
    "failed_without_error",
    "failed_token_missing",
    "failed_token_expired",
    "failed_missing_channel",
    "failed_unsupported_platform",
    "failed_missing_evidence",
    "failed_retrying",
    "failed_other",
    "retry_pending_schedules",
    "retry_pending_token_missing",
    "retry_pending_token_expired",
    "retry_pending_missing_channel",
    "retry_pending_unsupported_platform",
    "retry_pending_other",
    "token_missing_channels",
    "unsupported_connected_channels",
    "unknown_token_channels",
    "supported_connected_channels",
    "supported_healthy_channels",
    "published_evidence_count",
  ],
  benchmarking: [
    "token_missing_accounts",
    "collector_error_accounts",
    "manual_required_accounts",
    "manual_supported_accounts",
    "unimplemented_accounts",
    "no_data_accounts",
    "never_refreshed_accounts",
    "stale_refresh_accounts",
    "duplicate_source_accounts",
    "duplicate_source_connections",
    "placeholder_only_accounts",
    "mixed_accounts",
    "usable_live_supported_accounts",
    "live_supported_accounts",
    "live_accounts",
    "actual_metric_posts",
    "proxy_metric_posts",
    "benchmark_accounts",
    "benchmark_posts",
    "active_accounts",
  ],
  unknown: [],
}

function asRecord(value: unknown): Record<string, string | number | boolean | null> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, string | number | boolean | null>)
    : {}
}

function normalizeChannelsHealth(value: unknown): ChannelsHealth {
  if (!value || typeof value !== "object") return EMPTY_CHANNELS_HEALTH
  const data = value as Partial<ChannelsHealth>
  return {
    summary: {
      healthy: Number(data.summary?.healthy ?? 0),
      expiring: Number(data.summary?.expiring ?? 0),
      reauth_required: Number(data.summary?.reauth_required ?? 0),
      unknown: Number(data.summary?.unknown ?? 0),
      token_missing: Number(data.summary?.token_missing ?? 0),
    },
    items: Array.isArray(data.items) ? data.items : [],
  }
}

function normalizePipelineReadiness(value: unknown): PipelineReadiness {
  if (!value || typeof value !== "object") return EMPTY_PIPELINE_READINESS
  const data = value as Partial<PipelineReadiness>
  return {
    summary: {
      ready: Number(data.summary?.ready ?? 0),
      warning: Number(data.summary?.warning ?? 0),
      blocked: Number(data.summary?.blocked ?? 0),
    },
    items: Array.isArray(data.items)
      ? data.items.map((item) => ({
          key: String(item?.key ?? "unknown"),
          label: String(item?.label ?? "알 수 없음"),
          status: item?.status === "ready" || item?.status === "warning" || item?.status === "blocked" ? item.status : "blocked",
          summary: String(item?.summary ?? "상태 정보를 불러오지 못했습니다"),
          details: asRecord(item?.details),
        }))
      : [],
  }
}

function normalizePublishObservability(value: unknown): PublishObservability {
  if (!value || typeof value !== "object") return EMPTY_PUBLISH_OBSERVABILITY
  const data = value as Partial<PublishObservability>
  return {
    summary: {
      connected_channels: Number(data.summary?.connected_channels ?? 0),
      healthy_channels: Number(data.summary?.healthy_channels ?? 0),
      supported_connected_channels: Number(data.summary?.supported_connected_channels ?? 0),
      supported_healthy_channels: Number(data.summary?.supported_healthy_channels ?? 0),
      unsupported_connected_channels: Number(data.summary?.unsupported_connected_channels ?? 0),
      reauth_required_channels: Number(data.summary?.reauth_required_channels ?? 0),
      token_missing_channels: Number(data.summary?.token_missing_channels ?? 0),
      unknown_token_channels: Number(data.summary?.unknown_token_channels ?? 0),
      published_with_evidence: Number(data.summary?.published_with_evidence ?? 0),
      published_without_evidence: Number(data.summary?.published_without_evidence ?? 0),
      failed_with_error: Number(data.summary?.failed_with_error ?? 0),
      failed_without_error: Number(data.summary?.failed_without_error ?? 0),
      failed_with_stale_evidence: Number(data.summary?.failed_with_stale_evidence ?? 0),
      failed_missing_evidence: Number(data.summary?.failed_missing_evidence ?? 0),
      failed_unsupported_platform: Number(data.summary?.failed_unsupported_platform ?? 0),
      failed_token_expired: Number(data.summary?.failed_token_expired ?? 0),
      failed_token_missing: Number(data.summary?.failed_token_missing ?? 0),
      failed_missing_channel: Number(data.summary?.failed_missing_channel ?? 0),
      failed_retrying: Number(data.summary?.failed_retrying ?? 0),
      retry_pending_schedules: Number(data.summary?.retry_pending_schedules ?? 0),
      retry_pending_token_missing: Number(data.summary?.retry_pending_token_missing ?? 0),
      retry_pending_token_expired: Number(data.summary?.retry_pending_token_expired ?? 0),
      retry_pending_missing_channel: Number(data.summary?.retry_pending_missing_channel ?? 0),
      retry_pending_unsupported_platform: Number(data.summary?.retry_pending_unsupported_platform ?? 0),
      retry_pending_other: Number(data.summary?.retry_pending_other ?? 0),
      failed_other: Number(data.summary?.failed_other ?? 0),
    },
    published_items: Array.isArray(data.published_items) ? data.published_items : [],
    suspicious_items: Array.isArray(data.suspicious_items) ? data.suspicious_items : [],
    stale_evidence_items: Array.isArray((data as { stale_evidence_items?: unknown[] }).stale_evidence_items) ? (data as { stale_evidence_items: PublishObservability["stale_evidence_items"] }).stale_evidence_items : [],
    failed_items: Array.isArray(data.failed_items) ? data.failed_items : [],
    retry_pending_items: Array.isArray((data as { retry_pending_items?: unknown[] }).retry_pending_items) ? (data as { retry_pending_items: PublishObservability["retry_pending_items"] }).retry_pending_items : [],
  }
}

function normalizePipelineKey(value: string | undefined): PipelineKey {
  if (value === "ai_generation" || value === "oauth_connections" || value === "publishing" || value === "benchmarking") {
    return value
  }
  return "unknown"
}

function formatPipelineDetailValue(value: string | number | boolean | null | undefined): string {
  if (typeof value === "boolean") return value ? "예" : "아니오"
  if (value === null || value === undefined || value === "") return "-"
  return String(value)
}

function getPipelineDetailEntries(key: string, details: Record<string, string | number | boolean | null>): Array<[string, string | number | boolean | null]> {
  const normalizedKey = normalizePipelineKey(key)
  const orderedKeys = PIPELINE_DETAIL_ORDER[normalizedKey] || []
  const orderedEntries = orderedKeys
    .filter((detailKey) => Object.prototype.hasOwnProperty.call(details, detailKey))
    .map((detailKey) => [detailKey, details[detailKey]] as [string, string | number | boolean | null])
  const remainingEntries = Object.entries(details).filter(([detailKey]) => !orderedKeys.includes(detailKey))
  const limit = normalizedKey === "benchmarking"
    ? 14
    : normalizedKey === "publishing"
      ? 12
      : normalizedKey === "oauth_connections"
        ? 10
        : 6
  return [...orderedEntries, ...remainingEntries].slice(0, limit)
}

export default function DashboardPage() {
  const router = useRouter()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [channelsHealth, setChannelsHealth] = useState<ChannelsHealth | null>(null)
  const [pipelineReadiness, setPipelineReadiness] = useState<PipelineReadiness | null>(null)
  const [publishObservability, setPublishObservability] = useState<PublishObservability | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get("/api/v1/dashboard/stats"),
      api.get("/api/v1/dashboard/recent-activity"),
      api.get("/api/v1/dashboard/channels-health"),
      api.get("/api/v1/dashboard/pipeline-readiness"),
      api.get("/api/v1/dashboard/publish-observability"),
    ])
      .then(([statsRes, activityRes, healthRes, pipelineRes, publishRes]) => {
        setStats(statsRes.data)
        const activityItems = Array.isArray(activityRes.data)
          ? activityRes.data
          : Array.isArray(activityRes.data?.recent_contents)
            ? activityRes.data.recent_contents
            : []
        setActivity(activityItems)
        setChannelsHealth(normalizeChannelsHealth(healthRes.data))
        setPipelineReadiness(normalizePipelineReadiness(pipelineRes.data))
        setPublishObservability(normalizePublishObservability(publishRes.data))
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

  const healthBadge = (health: "healthy" | "expiring" | "reauth_required" | "unknown" | "token_missing") => {
    if (health === "healthy") return "bg-blue-50 text-blue-700"
    if (health === "expiring") return "bg-yellow-50 text-yellow-700"
    if (health === "reauth_required") return "bg-red-50 text-red-700"
    if (health === "token_missing") return "bg-rose-50 text-rose-700"
    return "bg-gray-100 text-gray-600"
  }

  const pipelineBadge = (status: "ready" | "warning" | "blocked") => {
    if (status === "ready") return "bg-blue-50 text-blue-700"
    if (status === "warning") return "bg-yellow-50 text-yellow-700"
    return "bg-red-50 text-red-700"
  }

  const failureBadge = (category?: string | null) => {
    if (category === "retrying") return "bg-amber-50 text-amber-700"
    if (category === "unsupported_platform" || category === "token_expired" || category === "token_missing" || category === "missing_channel") return "bg-rose-50 text-rose-700"
    if (category === "missing_evidence") return "bg-orange-50 text-orange-700"
    return "bg-gray-100 text-gray-700"
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
                <h2 className="text-sm font-semibold text-gray-700">핵심 파이프라인 준비도</h2>
                <p className="text-xs text-gray-400 mt-1">생성 · OAuth · 발행 · 벤치마킹의 실제 준비 상태를 먼저 봅니다</p>
              </div>
              <div className="text-xs text-gray-500">
                준비 {pipelineReadiness?.summary.ready ?? 0} · 경고 {pipelineReadiness?.summary.warning ?? 0} · 차단 {pipelineReadiness?.summary.blocked ?? 0}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              {(pipelineReadiness?.items || []).map((item) => (
                <div key={item.key} className="rounded-lg border px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-800">{item.label}</p>
                      <p className="text-xs text-gray-500 mt-1">{item.summary}</p>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${pipelineBadge(item.status)}`}>{item.status}</span>
                  </div>
                  <div className="mt-3 space-y-1">
                    {getPipelineDetailEntries(item.key, item.details || {}).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between text-xs text-gray-500 gap-3">
                        <span>{PIPELINE_DETAIL_LABELS[key] || key}</span>
                        <span className="font-medium text-gray-700 text-right">{formatPipelineDetailValue(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {(pipelineReadiness?.items || []).length === 0 && (
                <div className="col-span-2 text-sm text-gray-400 py-4 text-center">파이프라인 상태를 불러오지 못했습니다</div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border p-5 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-gray-700">발행 증거 / 실패 추적</h2>
                <p className="text-xs text-gray-400 mt-1">증거 있는 성공, 증거 없는 published, 최근 실패 사유를 분리해서 봅니다</p>
              </div>
              <div className="text-xs text-gray-500 text-right">
                <div>연결 {publishObservability?.summary.connected_channels ?? 0} · 정상 {publishObservability?.summary.healthy_channels ?? 0} · 재인증필요 {publishObservability?.summary.reauth_required_channels ?? 0}</div>
                <div className="mt-1">지원채널 {publishObservability?.summary.supported_connected_channels ?? 0} · 건강한 지원채널 {publishObservability?.summary.supported_healthy_channels ?? 0} · 미지원채널 {publishObservability?.summary.unsupported_connected_channels ?? 0}</div>
                <div className="mt-1">토큰없음 채널 {publishObservability?.summary.token_missing_channels ?? 0} · 토큰상태 미확인 {publishObservability?.summary.unknown_token_channels ?? 0}</div>
                <div className="mt-1">증거 {publishObservability?.summary.published_with_evidence ?? 0} · 의심 {publishObservability?.summary.published_without_evidence ?? 0} · 실패 {publishObservability?.summary.failed_with_error ?? 0} · 실패사유 미기록 {publishObservability?.summary.failed_without_error ?? 0} · 실패인데 증거남음 {publishObservability?.summary.failed_with_stale_evidence ?? 0}</div>
                <div className="mt-1">증거누락 {publishObservability?.summary.failed_missing_evidence ?? 0} · 미지원채널 {publishObservability?.summary.failed_unsupported_platform ?? 0} · 토큰만료 {publishObservability?.summary.failed_token_expired ?? 0}</div>
                <div className="mt-1">토큰없음 {publishObservability?.summary.failed_token_missing ?? 0} · 채널/콘텐츠 누락 {publishObservability?.summary.failed_missing_channel ?? 0} · 재시도 실패표시 {publishObservability?.summary.failed_retrying ?? 0} · 기타 {publishObservability?.summary.failed_other ?? 0}</div>
                <div className="mt-1">재시도 대기 {publishObservability?.summary.retry_pending_schedules ?? 0} · 토큰없음 {publishObservability?.summary.retry_pending_token_missing ?? 0} · 토큰만료 {publishObservability?.summary.retry_pending_token_expired ?? 0} · 채널누락 {publishObservability?.summary.retry_pending_missing_channel ?? 0} · 미지원 {publishObservability?.summary.retry_pending_unsupported_platform ?? 0} · 기타 {publishObservability?.summary.retry_pending_other ?? 0}</div>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
              <div className="rounded-lg border p-4">
                <h3 className="text-xs font-semibold text-gray-600 mb-3">최근 발행 증거</h3>
                <div className="space-y-2">
                  {(publishObservability?.published_items || []).slice(0, 5).map((item) => (
                    <div key={item.id} className="rounded-lg bg-blue-50 border border-blue-100 px-3 py-2">
                      <p className="text-sm font-medium text-gray-800 truncate">{item.title}</p>
                      <p className="text-[11px] text-gray-500 mt-1">채널: {item.channel_type || "-"}{item.account_name ? ` · ${item.account_name}` : ""}</p>
                      <p className="text-[11px] text-gray-500 mt-1">post_id: {item.platform_post_id || "-"}</p>
                      <p className="text-[11px] text-gray-500 truncate">url: {item.published_url || "-"}</p>
                    </div>
                  ))}
                  {(publishObservability?.published_items || []).length === 0 && (
                    <div className="text-sm text-gray-400 py-4 text-center">아직 발행 증거가 없습니다</div>
                  )}
                </div>
              </div>

              <div className="rounded-lg border p-4">
                <h3 className="text-xs font-semibold text-gray-600 mb-3">증거 없는 published</h3>
                <div className="space-y-2">
                  {(publishObservability?.suspicious_items || []).slice(0, 5).map((item) => (
                    <div key={item.id} className="rounded-lg bg-amber-50 border border-amber-100 px-3 py-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-800 truncate">{item.title}</p>
                        <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-medium ${failureBadge(item.failure_category)}`}>{item.failure_label || "증거 누락"}</span>
                      </div>
                      <p className="text-[11px] text-gray-500 mt-1">채널: {item.channel_type || "-"}{item.account_name ? ` · ${item.account_name}` : ""}</p>
                      <p className="text-[11px] text-amber-700 mt-1">published 상태지만 post_id / url 증거가 없습니다</p>
                      {item.schedule_status === "pending" && (item.schedule_retry_count ?? 0) > 0 && (
                        <p className="text-[11px] text-amber-700 mt-1">예약 재시도 대기 {item.schedule_retry_count}회 · 다음 예정 {item.schedule_scheduled_at ? new Date(item.schedule_scheduled_at).toLocaleString("ko-KR") : "-"}</p>
                      )}
                      {item.schedule_error_message && (
                        <p className="text-[11px] text-amber-800 mt-1 line-clamp-2">최근 스케줄 오류: {item.schedule_error_message}</p>
                      )}
                      <p className="text-[11px] text-gray-500 mt-1">업데이트 {item.updated_at ? new Date(item.updated_at).toLocaleString("ko-KR") : "-"}</p>
                    </div>
                  ))}
                  {(publishObservability?.suspicious_items || []).length === 0 && (
                    <div className="text-sm text-gray-400 py-4 text-center">증거 없는 published 항목이 없습니다</div>
                  )}
                </div>
              </div>

              <div className="rounded-lg border p-4">
                <h3 className="text-xs font-semibold text-gray-600 mb-3">실패인데 증거 남음</h3>
                <div className="space-y-2">
                  {(publishObservability?.stale_evidence_items || []).slice(0, 5).map((item) => (
                    <div key={item.id} className="rounded-lg bg-rose-50 border border-rose-100 px-3 py-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-800 truncate">{item.title}</p>
                        <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-medium ${failureBadge(item.failure_category)}`}>{item.failure_label || "기타 오류"}</span>
                      </div>
                      <p className="text-[11px] text-gray-500 mt-1">채널: {item.channel_type || "-"}{item.account_name ? ` · ${item.account_name}` : ""}</p>
                      <p className="text-[11px] text-rose-700 mt-1">failed 상태인데 post_id / url / published_at 증거가 남아 있습니다</p>
                      <p className="text-[11px] text-gray-500 mt-1">post_id: {item.platform_post_id || "-"}</p>
                      <p className="text-[11px] text-gray-500 truncate">url: {item.published_url || "-"}</p>
                      <p className="text-[11px] text-gray-500 mt-1">published_at: {item.published_at ? new Date(item.published_at).toLocaleString("ko-KR") : "-"}</p>
                    </div>
                  ))}
                  {(publishObservability?.stale_evidence_items || []).length === 0 && (
                    <div className="text-sm text-gray-400 py-4 text-center">실패인데 증거가 남은 항목이 없습니다</div>
                  )}
                </div>
              </div>

              <div className="rounded-lg border p-4">
                <h3 className="text-xs font-semibold text-gray-600 mb-3">최근 발행 실패</h3>
                <div className="space-y-2">
                  {(publishObservability?.failed_items || []).slice(0, 5).map((item) => (
                    <div key={item.id} className="rounded-lg bg-red-50 border border-red-100 px-3 py-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-800 truncate">{item.title}</p>
                        <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-medium ${failureBadge(item.failure_category)}`}>{item.failure_label || "기타 오류"}</span>
                      </div>
                      <p className="text-[11px] text-gray-500 mt-1">채널: {item.channel_type || "-"}{item.account_name ? ` · ${item.account_name}` : ""}</p>
                      {item.schedule_status === "pending" && (item.schedule_retry_count ?? 0) > 0 && (
                        <p className="text-[11px] text-amber-700 mt-1">예약 재시도 대기 {item.schedule_retry_count}회 · 다음 예정 {item.schedule_scheduled_at ? new Date(item.schedule_scheduled_at).toLocaleString("ko-KR") : "-"}</p>
                      )}
                      <p className="text-[11px] text-red-700 mt-1 line-clamp-2">{item.publish_error || item.schedule_error_message || "실패 상태인데 사유가 기록되지 않았습니다"}</p>
                    </div>
                  ))}
                  {(publishObservability?.failed_items || []).length === 0 && (
                    <div className="text-sm text-gray-400 py-4 text-center">최근 발행 실패가 없습니다</div>
                  )}
                </div>
              </div>

              <div className="rounded-lg border p-4">
                <h3 className="text-xs font-semibold text-gray-600 mb-3">재시도 대기 예약</h3>
                <div className="space-y-2">
                  {(publishObservability?.retry_pending_items || []).slice(0, 5).map((item) => (
                    <div key={item.schedule_id} className="rounded-lg bg-orange-50 border border-orange-100 px-3 py-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-800 truncate">{item.title}</p>
                        <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-medium ${failureBadge(item.failure_category)}`}>{item.failure_label || "기타 오류"}</span>
                      </div>
                      <p className="text-[11px] text-gray-500 mt-1">채널: {item.channel_type || "-"}{item.account_name ? ` · ${item.account_name}` : ""}</p>
                      <p className="text-[11px] text-orange-700 mt-1">재시도 {item.retry_count ?? 0}회 · 다음 예정 {item.scheduled_at ? new Date(item.scheduled_at).toLocaleString("ko-KR") : "-"}</p>
                      <p className="text-[11px] text-gray-500 mt-1">최근 갱신 {item.updated_at ? new Date(item.updated_at).toLocaleString("ko-KR") : "-"}</p>
                      <p className="text-[11px] text-orange-700 mt-1 line-clamp-2">{item.error_message || "최근 실패 사유 없음"}</p>
                    </div>
                  ))}
                  {(publishObservability?.retry_pending_items || []).length === 0 && (
                    <div className="text-sm text-gray-400 py-4 text-center">재시도 대기 예약이 없습니다</div>
                  )}
                </div>
              </div>
            </div>
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

            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
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
              <div className="rounded-lg bg-rose-50 px-4 py-3">
                <p className="text-xs text-rose-700">토큰 없음</p>
                <p className="text-xl font-bold text-rose-900">{channelsHealth?.summary.token_missing ?? 0}</p>
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
                    {item.health === "token_missing" ? (
                      <p className="text-xs text-rose-700 mt-0.5">연결은 보이지만 복호화 가능한 access token이 없습니다</p>
                    ) : item.token_expires_at ? (
                      <p className="text-xs text-gray-400 mt-0.5">만료시각: {new Date(item.token_expires_at).toLocaleString("ko-KR")}</p>
                    ) : (
                      <p className="text-xs text-gray-400 mt-0.5">만료시각 미확인</p>
                    )}
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${healthBadge(item.health)}`}>{item.health_label || item.health}</span>
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
