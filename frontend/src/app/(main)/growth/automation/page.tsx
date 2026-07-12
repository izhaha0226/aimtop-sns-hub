"use client"

import Link from "next/link"
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react"
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Circle,
  FileText,
  Inbox,
  Loader2,
  MessageSquare,
  Play,
  RefreshCw,
  Settings2,
  Sparkles,
  Zap,
} from "lucide-react"
import { useSelectedClient } from "@/hooks/useSelectedClient"
import {
  automationService,
  type AutomationAction,
  type AutomationPolicy,
  type AutomationRun,
} from "@/services/automation"

type StepId = "channels" | "materials" | "comments" | "results"
type BusyKey = "load" | "policy" | "material" | "comments" | null

const CHANNEL_META: Record<string, { emoji: string; name: string; short: string }> = {
  instagram: { emoji: "📸", name: "인스타그램", short: "카드/이미지 발행" },
  facebook: { emoji: "📘", name: "페이스북", short: "페이지 발행·댓글" },
  threads: { emoji: "🧵", name: "스레드", short: "짧은 글 발행" },
  x: { emoji: "𝕏", name: "X(트위터)", short: "짧은 글 발행" },
  youtube: { emoji: "▶️", name: "유튜브", short: "영상·댓글" },
  blog: { emoji: "✍️", name: "네이버 블로그", short: "장문 발행" },
  linkedin: { emoji: "💼", name: "링크드인", short: "전문 톤 발행" },
  kakao: { emoji: "💬", name: "카카오", short: "소재만 가능" },
  tiktok: { emoji: "🎵", name: "틱톡", short: "소재만 가능" },
}

const RUN_KIND_LABEL: Record<string, string> = {
  material: "소재 생성",
  comment_sync: "댓글 동기화",
  publish: "발행",
}

const ACTION_LABEL: Record<string, string> = {
  policy_upsert: "채널 설정 저장",
  material_variant_created: "채널 초안 생성",
  comment_sync: "댓글 가져오기",
  auto_reply: "자동 답글",
  comment_escalated: "위험 댓글 알림",
}

function channelLabel(platform: string) {
  return CHANNEL_META[platform]?.name || platform
}

function channelEmoji(platform: string) {
  return CHANNEL_META[platform]?.emoji || "🔗"
}

function formatTime(value?: string | null) {
  if (!value) return "-"
  try {
    return new Date(value).toLocaleString("ko-KR", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return value
  }
}

function extractError(error: unknown, fallback: string) {
  if (typeof error === "object" && error && "response" in error) {
    // @ts-expect-error axios error shape
    const detail = error.response?.data?.detail
    if (detail) return String(detail)
  }
  if (error instanceof Error) return error.message
  return fallback
}

export default function ChannelAutomationPage() {
  const { selectedClientId, selectedClient, loading: clientLoading } = useSelectedClient()
  const [policies, setPolicies] = useState<AutomationPolicy[]>([])
  const [runs, setRuns] = useState<AutomationRun[]>([])
  const [actions, setActions] = useState<AutomationAction[]>([])
  const [busy, setBusy] = useState<BusyKey>(null)
  const [errorMessage, setErrorMessage] = useState("")
  const [toast, setToast] = useState<{ type: "ok" | "info"; text: string; href?: string; hrefLabel?: string } | null>(null)
  const [activeStep, setActiveStep] = useState<StepId>("channels")
  const [showLogs, setShowLogs] = useState(false)
  const [title, setTitle] = useState("")
  const [brief, setBrief] = useState("")
  const [selectedChannels, setSelectedChannels] = useState<string[]>(["instagram", "facebook", "threads", "x"])
  const [lastMaterialCount, setLastMaterialCount] = useState(0)

  const loadAll = useCallback(async () => {
    if (!selectedClientId) return
    setBusy("load")
    setErrorMessage("")
    try {
      const [nextPolicies, nextRuns, nextActions] = await Promise.all([
        automationService.listPolicies(selectedClientId),
        automationService.listRuns(selectedClientId),
        automationService.listActions(selectedClientId),
      ])
      setPolicies(nextPolicies)
      setRuns(nextRuns)
      setActions(nextActions)

      const enabled = nextPolicies.filter((p) => p.enabled && p.capability?.automation_ready).map((p) => p.platform)
      if (enabled.length) {
        setSelectedChannels((prev) => {
          const kept = prev.filter((p) => enabled.includes(p))
          return kept.length ? kept : enabled.slice(0, 4)
        })
      }
    } catch (error) {
      setErrorMessage(extractError(error, "자동화 화면을 불러오지 못했습니다."))
    } finally {
      setBusy(null)
    }
  }, [selectedClientId])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  const enabledPolicies = useMemo(
    () => policies.filter((p) => p.enabled && p.capability?.automation_ready),
    [policies]
  )
  const readyPolicies = useMemo(
    () => policies.filter((p) => p.capability?.automation_ready),
    [policies]
  )
  const autoReplyOn = useMemo(
    () => policies.filter((p) => p.auto_reply_enabled).length,
    [policies]
  )
  const commentReady = useMemo(
    () => policies.filter((p) => p.capability?.comment_fetch).length,
    [policies]
  )

  const nextHint = useMemo(() => {
    if (!enabledPolicies.length) {
      return {
        step: "channels" as StepId,
        title: "먼저 돌릴 채널을 켜 주세요",
        body: "인스타그램·페이스북처럼 쓸 채널만 ON 하면 됩니다. 준비 안 된 채널은 자동으로 막혀 있어요.",
        cta: "1단계로 이동",
      }
    }
    if (!lastMaterialCount && !runs.some((r) => r.kind === "material" && r.status === "ok")) {
      return {
        step: "materials" as StepId,
        title: "이제 오늘 올릴 소재를 만들어 보세요",
        body: "주제 한 줄만 적으면 선택한 채널별 초안이 한꺼번에 생깁니다.",
        cta: "2단계로 이동",
      }
    }
    return {
      step: "comments" as StepId,
      title: "댓글도 자동으로 챙길 수 있어요",
      body: "게시 후 들어온 댓글을 가져오고, 안전한 문의는 자동 답글·위험 댓글은 인박스로 보냅니다.",
      cta: "3단계로 이동",
    }
  }, [enabledPolicies.length, lastMaterialCount, runs])

  const steps: Array<{ id: StepId; no: number; label: string; done: boolean }> = [
    { id: "channels", no: 1, label: "채널 켜기", done: enabledPolicies.length > 0 },
    {
      id: "materials",
      no: 2,
      label: "소재 만들기",
      done: lastMaterialCount > 0 || runs.some((r) => r.kind === "material" && r.status === "ok"),
    },
    {
      id: "comments",
      no: 3,
      label: "댓글 돌리기",
      done: runs.some((r) => r.kind === "comment_sync" && r.status === "ok"),
    },
    { id: "results", no: 4, label: "결과 확인", done: actions.length > 0 },
  ]

  const toggleChannel = (platform: string) => {
    setSelectedChannels((prev) =>
      prev.includes(platform) ? prev.filter((p) => p !== platform) : [...prev, platform]
    )
  }

  const updatePolicy = async (policy: AutomationPolicy, patch: Partial<AutomationPolicy>) => {
    if (!selectedClientId) return
    setBusy("policy")
    setErrorMessage("")
    setToast(null)
    try {
      await automationService.upsertPolicy(selectedClientId, policy.platform, {
        enabled: patch.enabled ?? policy.enabled,
        require_approval: patch.require_approval ?? policy.require_approval,
        daily_limit: patch.daily_limit ?? policy.daily_limit,
        auto_reply_enabled: patch.auto_reply_enabled ?? policy.auto_reply_enabled,
      })
      const name = channelLabel(policy.platform)
      if (patch.enabled !== undefined) {
        setToast({
          type: "ok",
          text: patch.enabled ? `${name} 자동화를 켰습니다.` : `${name} 자동화를 껐습니다.`,
        })
        if (patch.enabled) setActiveStep("materials")
      } else if (patch.auto_reply_enabled !== undefined) {
        setToast({
          type: "ok",
          text: patch.auto_reply_enabled ? `${name} 자동 답글을 켰습니다.` : `${name} 자동 답글을 껐습니다.`,
        })
      } else if (patch.require_approval !== undefined) {
        setToast({
          type: "ok",
          text: patch.require_approval
            ? `${name}은(는) 발행 전 승인이 필요합니다.`
            : `${name}은(는) 승인 없이 바로 진행합니다.`,
        })
      }
      await loadAll()
    } catch (error) {
      setErrorMessage(extractError(error, "채널 설정을 저장하지 못했습니다."))
    } finally {
      setBusy(null)
    }
  }

  const generateMaterials = async () => {
    if (!selectedClientId) return
    if (!title.trim()) {
      setErrorMessage("주제 제목을 입력해 주세요. 예: 봄 시즌 예약 이벤트")
      return
    }
    if (!selectedChannels.length) {
      setErrorMessage("초안을 만들 채널을 하나 이상 선택해 주세요.")
      return
    }
    setBusy("material")
    setErrorMessage("")
    setToast(null)
    try {
      const result = await automationService.generateMaterials({
        client_id: selectedClientId,
        title: title.trim(),
        brief: brief.trim() || undefined,
        channels: selectedChannels,
        require_approval: true,
        generate_images: false,
        use_fallback_storyline: true,
      })
      setLastMaterialCount(result.contents.length)
      setToast({
        type: "ok",
        text: `${result.contents.length}개 채널 초안이 만들어졌습니다. 콘텐츠 목록에서 확인하고 승인·발행하세요.`,
        href: "/contents",
        hrefLabel: "콘텐츠 목록 보기",
      })
      setActiveStep("results")
      await loadAll()
    } catch (error) {
      setErrorMessage(extractError(error, "소재 초안 생성에 실패했습니다."))
    } finally {
      setBusy(null)
    }
  }

  const syncComments = async () => {
    if (!selectedClientId) return
    setBusy("comments")
    setErrorMessage("")
    setToast(null)
    try {
      const result = await automationService.syncComments(selectedClientId)
      const newComments = Number(result.new_comments || 0)
      const autoReplied = Number(result.auto_replied || 0)
      const escalated = Number(result.escalated || 0)
      setToast({
        type: "ok",
        text: `댓글 ${newComments}건 수집 · 자동답글 ${autoReplied}건 · 확인 필요 ${escalated}건`,
        href: "/inbox",
        hrefLabel: "인박스 열기",
      })
      setActiveStep("results")
      await loadAll()
    } catch (error) {
      setErrorMessage(extractError(error, "댓글 동기화에 실패했습니다."))
    } finally {
      setBusy(null)
    }
  }

  if (clientLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-gray-500">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        클라이언트 정보를 불러오는 중…
      </div>
    )
  }

  if (!selectedClientId) {
    return (
      <div className="mx-auto max-w-2xl rounded-2xl border border-amber-200 bg-amber-50 p-8">
        <div className="text-sm font-semibold text-amber-800">클라이언트를 먼저 선택해 주세요</div>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">채널 자동화</h1>
        <p className="mt-3 text-sm leading-6 text-gray-600">
          자동화는 광고주(클라이언트) 단위로 동작합니다. 화면 상단의 클라이언트 선택 후 다시 들어와 주세요.
        </p>
        <Link
          href="/clients"
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-gray-900 px-4 py-2.5 text-sm font-semibold text-white"
        >
          클라이언트 목록으로 <ArrowRight size={16} />
        </Link>
      </div>
    )
  }

  const clientName = selectedClient?.name || "선택 클라이언트"

  return (
    <div className="mx-auto max-w-5xl space-y-5 pb-10">
      {/* Hero */}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 px-6 py-6 text-white">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-blue-100">
                <Zap size={13} /> 오늘 SNS 운영 한 번에
              </div>
              <h1 className="mt-3 text-2xl font-bold tracking-tight sm:text-3xl">채널 자동화</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-200">
                <span className="font-semibold text-white">{clientName}</span> 기준으로
                소재 만들기 → 승인/발행 → 댓글 응대를 순서대로 진행합니다.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void loadAll()}
              disabled={busy === "load"}
              className="inline-flex items-center gap-2 self-start rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm text-white hover:bg-white/15 disabled:opacity-50"
            >
              {busy === "load" ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              새로고침
            </button>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <StatCard label="켜 둔 채널" value={`${enabledPolicies.length}개`} hint={`자동화 가능 ${readyPolicies.length}개 중`} />
            <StatCard label="자동 답글" value={autoReplyOn ? `${autoReplyOn}개 채널` : "꺼짐"} hint={`댓글 지원 ${commentReady}개 채널`} />
            <StatCard
              label="최근 작업"
              value={runs[0] ? RUN_KIND_LABEL[runs[0].kind] || runs[0].kind : "아직 없음"}
              hint={runs[0] ? formatTime(runs[0].started_at) : "아래에서 시작해 보세요"}
            />
          </div>
        </div>

        {/* Step rail */}
        <div className="grid gap-2 border-t border-slate-100 p-3 sm:grid-cols-4">
          {steps.map((step) => {
            const active = activeStep === step.id
            return (
              <button
                key={step.id}
                type="button"
                onClick={() => setActiveStep(step.id)}
                className={`rounded-xl px-3 py-3 text-left transition ${
                  active
                    ? "bg-blue-600 text-white shadow-sm"
                    : "bg-slate-50 text-slate-700 hover:bg-slate-100"
                }`}
              >
                <div className="flex items-center gap-2 text-xs font-semibold opacity-80">
                  {step.done ? <CheckCircle2 size={14} /> : <Circle size={14} />}
                  {step.no}단계
                </div>
                <div className="mt-1 text-sm font-bold">{step.label}</div>
              </button>
            )
          })}
        </div>
      </section>

      {/* Guidance banner */}
      <section className="rounded-2xl border border-blue-100 bg-blue-50 px-5 py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-bold text-blue-900">{nextHint.title}</div>
            <p className="mt-1 text-sm leading-6 text-blue-800/90">{nextHint.body}</p>
          </div>
          <button
            type="button"
            onClick={() => setActiveStep(nextHint.step)}
            className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
          >
            {nextHint.cta} <ArrowRight size={16} />
          </button>
        </div>
      </section>

      {errorMessage ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{errorMessage}</div>
      ) : null}

      {toast ? (
        <div
          className={`rounded-xl border px-4 py-3 text-sm ${
            toast.type === "ok"
              ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : "border-slate-200 bg-slate-50 text-slate-800"
          }`}
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <span>{toast.text}</span>
            {toast.href ? (
              <Link href={toast.href} className="inline-flex items-center gap-1 font-semibold underline-offset-2 hover:underline">
                {toast.hrefLabel || "바로가기"} <ArrowRight size={14} />
              </Link>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* STEP 1 */}
      {activeStep === "channels" ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <SectionHeader
            no={1}
            title="돌릴 채널 선택"
            desc="자주 쓰는 채널만 켜 두면 됩니다. 준비되지 않은 채널은 회색으로 표시되고 켤 수 없습니다."
          />
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {policies.map((policy) => {
              const ready = Boolean(policy.capability?.automation_ready)
              const publish = Boolean(policy.capability?.publish)
              const comments = Boolean(policy.capability?.comment_fetch)
              const meta = CHANNEL_META[policy.platform]
              return (
                <article
                  key={policy.platform}
                  className={`rounded-2xl border p-4 transition ${
                    policy.enabled
                      ? "border-blue-300 bg-blue-50/40"
                      : ready
                        ? "border-slate-200 bg-white"
                        : "border-slate-100 bg-slate-50 opacity-80"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{channelEmoji(policy.platform)}</span>
                        <div>
                          <div className="font-bold text-slate-900">{channelLabel(policy.platform)}</div>
                          <div className="text-xs text-slate-500">{meta?.short || policy.capability?.notes}</div>
                        </div>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        <Pill ok={publish} yes="발행 가능" no="발행 준비 중" />
                        <Pill ok={comments} yes="댓글 가능" no="댓글 미지원" />
                        <Pill ok={ready} yes="자동화 가능" no="아직 준비 중" />
                      </div>
                      {!ready && (policy.capability?.blockers || []).length > 0 ? (
                        <p className="mt-2 text-xs leading-5 text-amber-700">
                          이유: {(policy.capability?.blockers || []).slice(0, 2).join(" · ")}
                        </p>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      disabled={!ready || busy === "policy"}
                      onClick={() => void updatePolicy(policy, { enabled: !policy.enabled })}
                      className={`relative h-8 w-14 shrink-0 rounded-full transition disabled:cursor-not-allowed disabled:opacity-40 ${
                        policy.enabled ? "bg-blue-600" : "bg-slate-300"
                      }`}
                      aria-label={`${channelLabel(policy.platform)} 자동화 ${policy.enabled ? "끄기" : "켜기"}`}
                    >
                      <span
                        className={`absolute top-1 h-6 w-6 rounded-full bg-white shadow transition ${
                          policy.enabled ? "left-7" : "left-1"
                        }`}
                      />
                    </button>
                  </div>

                  {policy.enabled ? (
                    <div className="mt-4 grid gap-2 border-t border-blue-100 pt-3 sm:grid-cols-2">
                      <OptionToggle
                        label="발행 전 승인"
                        description="담당자 확인 후 발행"
                        checked={policy.require_approval}
                        disabled={busy === "policy"}
                        onChange={() => void updatePolicy(policy, { require_approval: !policy.require_approval })}
                      />
                      <OptionToggle
                        label="자동 답글"
                        description={comments ? "안전한 문의만 자동 응답" : "이 채널은 댓글 미지원"}
                        checked={policy.auto_reply_enabled}
                        disabled={busy === "policy" || !comments}
                        onChange={() => void updatePolicy(policy, { auto_reply_enabled: !policy.auto_reply_enabled })}
                      />
                    </div>
                  ) : null}
                </article>
              )
            })}
          </div>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-500">
              지금 <span className="font-semibold text-slate-800">{enabledPolicies.length}개</span> 채널이 켜져 있습니다.
            </p>
            <button
              type="button"
              onClick={() => setActiveStep("materials")}
              disabled={!enabledPolicies.length}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
            >
              다음: 소재 만들기 <ArrowRight size={16} />
            </button>
          </div>
        </section>
      ) : null}

      {/* STEP 2 */}
      {activeStep === "materials" ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <SectionHeader
            no={2}
            title="소재 한 번에 만들기"
            desc="주제만 적으면 채널별 말투·길이에 맞춰 초안이 생성됩니다. 결과는 콘텐츠 목록에 ‘승인 대기’로 저장됩니다."
          />

          <div className="mt-5 space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-sm font-semibold text-slate-800">오늘 무엇에 대해 올릴까요?</span>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="예: 봄 시즌 상담 예약 이벤트"
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none ring-blue-500 focus:ring-2"
              />
            </label>

            <label className="block">
              <span className="mb-1.5 block text-sm font-semibold text-slate-800">
                조금만 더 알려주세요 <span className="font-normal text-slate-400">(선택)</span>
              </span>
              <textarea
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                placeholder="예: 주말 방문 고객 대상, 예약 시 10% 할인, 따뜻한 톤으로"
                className="min-h-[100px] w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none ring-blue-500 focus:ring-2"
              />
            </label>

            <div>
              <div className="mb-2 text-sm font-semibold text-slate-800">어느 채널 초안을 만들까요?</div>
              <div className="flex flex-wrap gap-2">
                {policies
                  .filter((p) => p.capability?.material_variant)
                  .map((policy) => {
                    const selected = selectedChannels.includes(policy.platform)
                    return (
                      <button
                        key={policy.platform}
                        type="button"
                        onClick={() => toggleChannel(policy.platform)}
                        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition ${
                          selected
                            ? "border-blue-600 bg-blue-600 text-white"
                            : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                        }`}
                      >
                        <span>{channelEmoji(policy.platform)}</span>
                        {channelLabel(policy.platform)}
                      </button>
                    )
                  })}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                추천: 켜 둔 채널 기준으로 선택 · 현재 {selectedChannels.length}개 선택
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={busy === "material"}
                onClick={() => void generateMaterials()}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white shadow-sm hover:bg-blue-700 disabled:opacity-40"
              >
                {busy === "material" ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                초안 만들기
              </button>
              <Link
                href="/contents"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                <FileText size={16} /> 콘텐츠 목록
              </Link>
            </div>

            <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
              <div className="font-semibold text-slate-800">이렇게 진행됩니다</div>
              <ol className="mt-1 list-decimal space-y-1 pl-5">
                <li>채널별 초안이 승인 대기로 저장됩니다.</li>
                <li>콘텐츠 목록에서 문구를 확인하고 승인합니다.</li>
                <li>연결된 채널로 예약·즉시 발행할 수 있습니다.</li>
              </ol>
            </div>
          </div>
        </section>
      ) : null}

      {/* STEP 3 */}
      {activeStep === "comments" ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <SectionHeader
            no={3}
            title="댓글 자동 챙기기"
            desc="연결된 채널의 새 댓글을 가져옵니다. 안전한 문의는 자동 답글, 환불·욕설·법적 이슈는 인박스로 넘깁니다."
          />

          <div className="mt-5 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
              <div className="text-sm font-semibold text-slate-800">지금 한 번 실행</div>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                보통 몇 초~수십 초 걸립니다. 결과는 아래 활동 기록과 인박스에서 확인할 수 있습니다.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={busy === "comments"}
                  onClick={() => void syncComments()}
                  className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-40"
                >
                  {busy === "comments" ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                  댓글 지금 가져오기
                </button>
                <Link
                  href="/inbox"
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700"
                >
                  <Inbox size={16} /> 인박스 열기
                </Link>
              </div>
              <p className="mt-4 text-xs text-slate-500">
                자동화가 켜진 클라이언트는 약 15분마다 백그라운드에서도 댓글을 확인합니다.
              </p>
            </div>

            <div className="space-y-3">
              <InfoTile
                icon={<MessageSquare size={16} className="text-blue-600" />}
                title="자동 답글이 켜진 채널"
                body={autoReplyOn ? `${autoReplyOn}개 채널` : "아직 없습니다. 1단계에서 채널 카드의 ‘자동 답글’을 켜 주세요."}
              />
              <InfoTile
                icon={<Settings2 size={16} className="text-amber-600" />}
                title="위험 댓글 처리"
                body="환불·고소·욕설 등은 자동으로 답하지 않고 인박스에서 확인하도록 표시합니다."
              />
              <InfoTile
                icon={<CheckCircle2 size={16} className="text-emerald-600" />}
                title="댓글 지원 채널"
                body="인스타그램, 페이스북, 스레드, 유튜브 중심으로 동작합니다."
              />
            </div>
          </div>
        </section>
      ) : null}

      {/* STEP 4 + always-available quick results when selected */}
      {activeStep === "results" ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <SectionHeader
            no={4}
            title="결과 확인 · 다음 액션"
            desc="방금 한 작업의 결과와, 운영자가 이어서 할 일을 보여 줍니다."
          />

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <QuickLink
              href="/contents"
              title="콘텐츠 확인"
              desc="만든 초안 승인·발행"
              icon={<FileText size={18} />}
            />
            <QuickLink
              href="/inbox"
              title="인박스"
              desc="댓글·위험 이슈 확인"
              icon={<Inbox size={18} />}
            />
            <QuickLink
              href="/calendar"
              title="캘린더"
              desc="예약 발행 일정"
              icon={<Sparkles size={18} />}
            />
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-100 p-4">
              <div className="mb-3 text-sm font-bold text-slate-900">최근 작업</div>
              <div className="max-h-72 space-y-2 overflow-auto">
                {runs.length === 0 ? (
                  <EmptyState text="아직 실행한 작업이 없습니다. 2단계에서 소재를 만들어 보세요." />
                ) : (
                  runs.slice(0, 8).map((run) => (
                    <div key={run.id} className="rounded-lg border border-slate-100 px-3 py-2.5 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-slate-800">{RUN_KIND_LABEL[run.kind] || run.kind}</span>
                        <StatusChip ok={run.status === "ok"} label={run.status === "ok" ? "성공" : run.status === "running" ? "진행 중" : "확인 필요"} />
                      </div>
                      <div className="mt-1 text-xs text-slate-500">{formatTime(run.started_at)}</div>
                      {run.error ? <div className="mt-1 text-xs text-rose-600">{run.error}</div> : null}
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-100 p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="text-sm font-bold text-slate-900">상세 기록</div>
                <button
                  type="button"
                  onClick={() => setShowLogs((v) => !v)}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500"
                >
                  {showLogs ? "접기" : "펼치기"}
                  {showLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
              </div>
              {showLogs ? (
                <div className="max-h-72 space-y-2 overflow-auto">
                  {actions.length === 0 ? (
                    <EmptyState text="아직 상세 기록이 없습니다." />
                  ) : (
                    actions.slice(0, 20).map((action) => (
                      <div key={action.id} className="rounded-lg border border-slate-100 px-3 py-2.5 text-sm">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-slate-800">
                            {ACTION_LABEL[action.action] || action.action}
                            {action.platform ? ` · ${channelLabel(action.platform)}` : ""}
                          </span>
                          <StatusChip ok={action.ok} label={action.ok ? "완료" : "실패"} />
                        </div>
                        {action.error ? <div className="mt-1 text-xs text-rose-600">{action.error}</div> : null}
                        <div className="mt-1 text-xs text-slate-500">{formatTime(action.created_at)}</div>
                      </div>
                    ))
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-500">필요하면 펼쳐서 채널별 세부 기록을 확인할 수 있습니다.</p>
              )}
            </div>
          </div>
        </section>
      ) : null}

      {/* Bottom sticky-style helper */}
      <section className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-slate-600">
            막히면 이 순서만 기억하세요:{" "}
            <span className="font-semibold text-slate-900">채널 켜기 → 소재 만들기 → 콘텐츠 승인 → 댓글 확인</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setActiveStep("channels")}
              className="rounded-lg border px-3 py-1.5 text-xs font-semibold text-slate-600"
            >
              1 채널
            </button>
            <button
              type="button"
              onClick={() => setActiveStep("materials")}
              className="rounded-lg border px-3 py-1.5 text-xs font-semibold text-slate-600"
            >
              2 소재
            </button>
            <button
              type="button"
              onClick={() => setActiveStep("comments")}
              className="rounded-lg border px-3 py-1.5 text-xs font-semibold text-slate-600"
            >
              3 댓글
            </button>
            <button
              type="button"
              onClick={() => setActiveStep("results")}
              className="rounded-lg border px-3 py-1.5 text-xs font-semibold text-slate-600"
            >
              4 결과
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

function SectionHeader({ no, title, desc }: { no: number; title: string; desc: string }) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wide text-blue-600">{no}단계</div>
      <h2 className="mt-1 text-xl font-bold text-slate-900">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-500">{desc}</p>
    </div>
  )
}

function StatCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
      <div className="text-xs text-slate-300">{label}</div>
      <div className="mt-1 text-xl font-bold text-white">{value}</div>
      <div className="mt-1 text-xs text-slate-300">{hint}</div>
    </div>
  )
}

function Pill({ ok, yes, no }: { ok: boolean; yes: string; no: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
        ok ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200" : "bg-slate-100 text-slate-500 ring-1 ring-slate-200"
      }`}
    >
      {ok ? yes : no}
    </span>
  )
}

function OptionToggle({
  label,
  description,
  checked,
  disabled,
  onChange,
}: {
  label: string
  description: string
  checked: boolean
  disabled?: boolean
  onChange: () => void
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onChange}
      className={`rounded-xl border px-3 py-2 text-left disabled:opacity-40 ${
        checked ? "border-blue-200 bg-white" : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-slate-800">{label}</span>
        <span className={`text-xs font-bold ${checked ? "text-blue-600" : "text-slate-400"}`}>{checked ? "ON" : "OFF"}</span>
      </div>
      <div className="mt-1 text-xs text-slate-500">{description}</div>
    </button>
  )
}

function InfoTile({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-xl border border-slate-100 bg-white p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        {icon}
        {title}
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  )
}

function QuickLink({
  href,
  title,
  desc,
  icon,
}: {
  href: string
  title: string
  desc: string
  icon: ReactNode
}) {
  return (
    <Link href={href} className="rounded-xl border border-slate-200 p-4 transition hover:border-blue-300 hover:bg-blue-50/40">
      <div className="flex items-center gap-2 text-slate-800">
        {icon}
        <span className="font-bold">{title}</span>
      </div>
      <p className="mt-2 text-sm text-slate-500">{desc}</p>
    </Link>
  )
}

function StatusChip({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${ok ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
      {label}
    </span>
  )
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-lg border border-dashed border-slate-200 px-3 py-8 text-center text-sm text-slate-400">{text}</div>
}
