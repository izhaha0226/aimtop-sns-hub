"use client"

import Link from "next/link"
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react"
import {
  ArrowRight,
  CheckCircle2,
  Circle,
  Eye,
  FileText,
  Inbox,
  Loader2,
  MessageSquare,
  Megaphone,
  RefreshCw,
  Rocket,
  Share2,
  Sparkles,
} from "lucide-react"
import { useSelectedClient } from "@/hooks/useSelectedClient"
import { automationService, type AutomationAction, type AutomationPolicy, type AutomationRun } from "@/services/automation"
import { contentsService } from "@/services/contents"
import type { Content } from "@/types/content"
import { STATUS_COLORS, STATUS_LABELS } from "@/types/content"

/** 운영 파이프라인: 카드뉴스 → 릴리즈 → 모니터링 → 댓글 → 확산 */
type StageId = "cardnews" | "release" | "monitor" | "comments" | "spread"
type BusyKey = "load" | "material" | "comments" | "approve" | "publish" | null

const STAGES: Array<{
  id: StageId
  no: number
  label: string
  short: string
  icon: typeof Sparkles
}> = [
  { id: "cardnews", no: 1, label: "카드뉴스 만들기", short: "소재", icon: Sparkles },
  { id: "release", no: 2, label: "릴리즈", short: "승인·발행", icon: Rocket },
  { id: "monitor", no: 3, label: "모니터링", short: "상태 추적", icon: Eye },
  { id: "comments", no: 4, label: "댓글 확인·답글", short: "응대", icon: MessageSquare },
  { id: "spread", no: 5, label: "확산", short: "리퍼포즈", icon: Share2 },
]

const CHANNEL_OPTIONS = [
  { id: "instagram", label: "인스타그램", emoji: "📸" },
  { id: "facebook", label: "페이스북", emoji: "📘" },
  { id: "threads", label: "스레드", emoji: "🧵" },
  { id: "x", label: "X", emoji: "𝕏" },
  { id: "linkedin", label: "링크드인", emoji: "💼" },
  { id: "blog", label: "블로그", emoji: "✍️" },
  { id: "youtube", label: "유튜브", emoji: "▶️" },
  { id: "kakao", label: "카카오", emoji: "💬" },
]

function extractError(error: unknown, fallback: string) {
  if (typeof error === "object" && error && "response" in error) {
    // @ts-expect-error axios
    const detail = error.response?.data?.detail
    if (detail) return String(detail)
  }
  if (error instanceof Error) return error.message
  return fallback
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

function isReleaseReady(c: Content) {
  return ["draft", "pending_approval", "approved", "rejected"].includes(c.status)
}

function isLiveOrScheduled(c: Content) {
  return ["published", "scheduled", "failed"].includes(c.status)
}

export default function ChannelAutomationPage() {
  const { selectedClientId, selectedClient, loading: clientLoading } = useSelectedClient()
  const [stage, setStage] = useState<StageId>("cardnews")
  const [busy, setBusy] = useState<BusyKey>(null)
  const [errorMessage, setErrorMessage] = useState("")
  const [toast, setToast] = useState<{ text: string; href?: string; hrefLabel?: string } | null>(null)

  const [policies, setPolicies] = useState<AutomationPolicy[]>([])
  const [runs, setRuns] = useState<AutomationRun[]>([])
  const [actions, setActions] = useState<AutomationAction[]>([])
  const [contents, setContents] = useState<Content[]>([])

  const [title, setTitle] = useState("")
  const [brief, setBrief] = useState("")
  const [channels, setChannels] = useState<string[]>(["instagram", "facebook", "threads"])
  const [actingId, setActingId] = useState<string | null>(null)

  const loadAll = useCallback(async () => {
    if (!selectedClientId) return
    setBusy("load")
    setErrorMessage("")
    try {
      const [nextPolicies, nextRuns, nextActions, nextContents] = await Promise.all([
        automationService.listPolicies(selectedClientId),
        automationService.listRuns(selectedClientId),
        automationService.listActions(selectedClientId),
        contentsService.list({ client_id: selectedClientId }),
      ])
      setPolicies(nextPolicies)
      setRuns(nextRuns)
      setActions(nextActions)
      setContents(Array.isArray(nextContents) ? nextContents : [])
    } catch (error) {
      setErrorMessage(extractError(error, "운영 현황을 불러오지 못했습니다."))
    } finally {
      setBusy(null)
    }
  }, [selectedClientId])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  const releaseQueue = useMemo(
    () => contents.filter(isReleaseReady).slice(0, 20),
    [contents]
  )
  const monitorItems = useMemo(
    () => contents.filter(isLiveOrScheduled).slice(0, 20),
    [contents]
  )
  const publishedCount = useMemo(
    () => contents.filter((c) => c.status === "published").length,
    [contents]
  )
  const pendingCount = useMemo(
    () => contents.filter((c) => c.status === "pending_approval" || c.status === "draft").length,
    [contents]
  )
  const failedCount = useMemo(
    () => contents.filter((c) => c.status === "failed").length,
    [contents]
  )
  const evidenceCount = useMemo(
    () => contents.filter((c) => c.status === "published" && (c.platform_post_id || c.published_url)).length,
    [contents]
  )
  const commentActions = useMemo(
    () => actions.filter((a) => ["comment_sync", "auto_reply", "comment_escalated"].includes(a.action)).slice(0, 12),
    [actions]
  )

  const stageDone: Record<StageId, boolean> = {
    cardnews: runs.some((r) => r.kind === "material" && r.status === "ok") || pendingCount > 0,
    release: publishedCount > 0 || contents.some((c) => c.status === "approved" || c.status === "scheduled"),
    monitor: publishedCount > 0 || failedCount > 0 || contents.some((c) => c.status === "scheduled"),
    comments: runs.some((r) => r.kind === "comment_sync") || commentActions.length > 0,
    spread: publishedCount > 0,
  }

  const nextStageHint = useMemo(() => {
    if (!stageDone.cardnews) {
      return {
        stage: "cardnews" as StageId,
        title: "먼저 카드뉴스를 만드세요",
        body: "주제 한 줄이면 채널별 카드뉴스 초안이 생성됩니다.",
      }
    }
    if (!stageDone.release) {
      return {
        stage: "release" as StageId,
        title: "릴리즈 단계로 넘어가세요",
        body: "만든 초안을 승인하고 발행(또는 예약)합니다.",
      }
    }
    if (!stageDone.monitor) {
      return {
        stage: "monitor" as StageId,
        title: "발행 상태를 모니터링하세요",
        body: "성공 증거·실패·예약 현황을 확인합니다.",
      }
    }
    if (!stageDone.comments) {
      return {
        stage: "comments" as StageId,
        title: "댓글을 확인하고 답글을 작성하세요",
        body: "새 댓글을 가져오고, 자동 답글·수동 응대를 진행합니다.",
      }
    }
    return {
      stage: "spread" as StageId,
      title: "성과 좋은 콘텐츠를 확산하세요",
      body: "다른 채널 재가공, 해시태그·바이럴 루프로 확산을 이어갑니다.",
    }
  }, [stageDone])

  const toggleChannel = (id: string) => {
    setChannels((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const createCardNews = async () => {
    if (!selectedClientId) return
    if (!title.trim()) {
      setErrorMessage("카드뉴스 주제를 입력해 주세요. 예: 봄 시즌 예약 이벤트 5장")
      return
    }
    if (!channels.length) {
      setErrorMessage("배포할 채널을 하나 이상 선택해 주세요.")
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
        channels,
        require_approval: true,
        generate_images: false,
        use_fallback_storyline: true,
      })
      setToast({
        text: `카드뉴스 초안 ${result.contents.length}개가 만들어졌습니다. 이제 릴리즈 단계에서 승인·발행하세요.`,
        href: undefined,
        hrefLabel: undefined,
      })
      setStage("release")
      await loadAll()
    } catch (error) {
      setErrorMessage(extractError(error, "카드뉴스 생성에 실패했습니다."))
    } finally {
      setBusy(null)
    }
  }

  const approveOne = async (id: string) => {
    setActingId(id)
    setBusy("approve")
    setErrorMessage("")
    try {
      await contentsService.approveContent(id)
      setToast({ text: "승인되었습니다. 이어서 발행하거나 예약을 진행하세요." })
      await loadAll()
    } catch (error) {
      setErrorMessage(extractError(error, "승인에 실패했습니다."))
    } finally {
      setBusy(null)
      setActingId(null)
    }
  }

  const requestApprovalOne = async (id: string) => {
    setActingId(id)
    setBusy("approve")
    setErrorMessage("")
    try {
      await contentsService.requestApproval(id)
      setToast({ text: "승인 요청 상태로 올렸습니다." })
      await loadAll()
    } catch (error) {
      setErrorMessage(extractError(error, "승인 요청에 실패했습니다."))
    } finally {
      setBusy(null)
      setActingId(null)
    }
  }

  const publishOne = async (id: string) => {
    setActingId(id)
    setBusy("publish")
    setErrorMessage("")
    try {
      const updated = await contentsService.publishNow(id)
      const hasEvidence = Boolean(updated.platform_post_id || updated.published_url)
      setToast({
        text: hasEvidence
          ? "발행 완료. 플랫폼 게시 증거까지 확인됐습니다."
          : "발행 처리됐지만 외부 게시 증거가 없습니다. 모니터링에서 확인하세요.",
      })
      setStage("monitor")
      await loadAll()
    } catch (error) {
      setErrorMessage(extractError(error, "발행에 실패했습니다. 채널 연동·토큰을 확인하세요."))
    } finally {
      setBusy(null)
      setActingId(null)
    }
  }

  const syncComments = async () => {
    if (!selectedClientId) return
    setBusy("comments")
    setErrorMessage("")
    setToast(null)
    try {
      const result = await automationService.syncComments(selectedClientId)
      setToast({
        text: `댓글 ${Number(result.new_comments || 0)}건 수집 · 자동답글 ${Number(result.auto_replied || 0)}건 · 확인필요 ${Number(result.escalated || 0)}건`,
        href: "/inbox",
        hrefLabel: "인박스에서 답글 작성",
      })
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
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 불러오는 중…
      </div>
    )
  }

  if (!selectedClientId) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl border border-amber-200 bg-amber-50 p-8">
        <h1 className="text-2xl font-bold">채널 자동화</h1>
        <p className="mt-3 text-sm leading-6 text-gray-600">
          카드뉴스 → 릴리즈 → 모니터링 → 댓글 → 확산 파이프라인은 클라이언트 단위로 동작합니다.
          상단에서 클라이언트를 먼저 선택해 주세요.
        </p>
        <Link href="/clients" className="mt-5 inline-flex items-center gap-2 rounded-xl bg-gray-900 px-4 py-2.5 text-sm font-semibold text-white">
          클라이언트 선택 <ArrowRight size={16} />
        </Link>
      </div>
    )
  }

  const clientName = selectedClient?.name || "선택 클라이언트"

  return (
    <div className="mx-auto max-w-5xl space-y-5 pb-12">
      {/* Header */}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-800 px-6 py-6 text-white">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-indigo-100">
                <Megaphone size={13} /> SNS 운영 파이프라인
              </div>
              <h1 className="mt-3 text-2xl font-bold sm:text-3xl">채널 자동화</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-200">
                <span className="font-semibold text-white">{clientName}</span> ·{" "}
                카드뉴스 제작 → 릴리즈 → 모니터링 → 댓글/답글 → 확산
              </p>
            </div>
            <button
              type="button"
              onClick={() => void loadAll()}
              disabled={busy === "load"}
              className="inline-flex items-center gap-2 self-start rounded-xl border border-white/15 bg-white/10 px-3 py-2 text-sm hover:bg-white/15 disabled:opacity-50"
            >
              {busy === "load" ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              새로고침
            </button>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <MiniStat label="승인 대기" value={`${pendingCount}`} />
            <MiniStat label="발행됨" value={`${publishedCount}`} />
            <MiniStat label="실패" value={`${failedCount}`} />
            <MiniStat label="게시 증거" value={`${evidenceCount}`} />
          </div>
        </div>

        {/* Pipeline steps */}
        <div className="grid gap-1 border-t border-slate-100 p-2 sm:grid-cols-5">
          {STAGES.map((s, idx) => {
            const active = stage === s.id
            const done = stageDone[s.id]
            const Icon = s.icon
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setStage(s.id)}
                className={`relative rounded-xl px-2.5 py-3 text-left transition ${
                  active ? "bg-indigo-600 text-white shadow-sm" : "bg-slate-50 text-slate-700 hover:bg-slate-100"
                }`}
              >
                <div className="flex items-center gap-1.5 text-[11px] font-semibold opacity-80">
                  {done ? <CheckCircle2 size={12} /> : <Circle size={12} />}
                  {s.no}단계
                  {idx < STAGES.length - 1 ? (
                    <span className={`ml-auto hidden text-[10px] sm:inline ${active ? "text-indigo-100" : "text-slate-400"}`}>→</span>
                  ) : null}
                </div>
                <div className="mt-1 flex items-center gap-1.5">
                  <Icon size={14} />
                  <span className="text-sm font-bold leading-tight">{s.label}</span>
                </div>
                <div className={`mt-0.5 text-[11px] ${active ? "text-indigo-100" : "text-slate-500"}`}>{s.short}</div>
              </button>
            )
          })}
        </div>
      </section>

      {/* Next action */}
      <section className="rounded-2xl border border-indigo-100 bg-indigo-50 px-5 py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-bold text-indigo-950">{nextStageHint.title}</div>
            <p className="mt-1 text-sm leading-6 text-indigo-900/80">{nextStageHint.body}</p>
          </div>
          <button
            type="button"
            onClick={() => setStage(nextStageHint.stage)}
            className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            해당 단계로 이동 <ArrowRight size={16} />
          </button>
        </div>
      </section>

      {errorMessage ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{errorMessage}</div>
      ) : null}
      {toast ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <span>{toast.text}</span>
            {toast.href ? (
              <Link href={toast.href} className="inline-flex items-center gap-1 font-semibold underline-offset-2 hover:underline">
                {toast.hrefLabel} <ArrowRight size={14} />
              </Link>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* ===== 1. 카드뉴스 ===== */}
      {stage === "cardnews" ? (
        <StagePanel
          no={1}
          title="카드뉴스 만들기"
          desc="한 주제로 5장 흐름의 카드뉴스 초안을 만들고, 선택한 채널 말투로 변형해 저장합니다."
        >
          <div className="space-y-4">
            <Field label="카드뉴스 주제" required>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="예: 봄 시즌 상담 예약, 5장으로 설득하기"
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none ring-indigo-500 focus:ring-2"
              />
            </Field>
            <Field label="핵심 메시지 / 브리프" optional>
              <textarea
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                placeholder="예: 주말 방문 고객, 예약 시 혜택, 따뜻하고 신뢰감 있는 톤"
                className="min-h-[96px] w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none ring-indigo-500 focus:ring-2"
              />
            </Field>
            <div>
              <div className="mb-2 text-sm font-semibold text-slate-800">어느 채널에 맞게 만들까요?</div>
              <div className="flex flex-wrap gap-2">
                {CHANNEL_OPTIONS.map((ch) => {
                  const on = channels.includes(ch.id)
                  return (
                    <button
                      key={ch.id}
                      type="button"
                      onClick={() => toggleChannel(ch.id)}
                      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm ${
                        on ? "border-indigo-600 bg-indigo-600 text-white" : "border-slate-200 bg-white text-slate-600"
                      }`}
                    >
                      <span>{ch.emoji}</span>
                      {ch.label}
                    </button>
                  )
                })}
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                disabled={busy === "material"}
                onClick={() => void createCardNews()}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-40"
              >
                {busy === "material" ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                카드뉴스 초안 생성
              </button>
              <Link
                href="/contents/new/topic"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700"
              >
                상세 제작 화면
              </Link>
            </div>
            <ol className="list-decimal space-y-1 rounded-xl bg-slate-50 px-5 py-4 text-sm leading-6 text-slate-600 pl-8">
              <li>5장 스토리라인 초안 생성</li>
              <li>채널별 문구 길이·톤 자동 변형</li>
              <li>승인 대기 상태로 콘텐츠 목록에 저장 → <strong>2. 릴리즈</strong></li>
            </ol>
          </div>
        </StagePanel>
      ) : null}

      {/* ===== 2. 릴리즈 ===== */}
      {stage === "release" ? (
        <StagePanel
          no={2}
          title="릴리즈"
          desc="카드뉴스 초안을 검토하고 승인 → 즉시 발행 또는 예약 발행으로 내보냅니다."
        >
          <div className="mb-4 flex flex-wrap gap-2">
            <Link href="/contents" className="rounded-lg border px-3 py-2 text-sm font-semibold text-slate-700">
              전체 콘텐츠
            </Link>
            <Link href="/calendar" className="rounded-lg border px-3 py-2 text-sm font-semibold text-slate-700">
              예약 캘린더
            </Link>
          </div>

          {releaseQueue.length === 0 ? (
            <Empty
              text="릴리즈할 초안이 없습니다."
              actionLabel="1단계: 카드뉴스 만들기"
              onAction={() => setStage("cardnews")}
            />
          ) : (
            <div className="space-y-3">
              {releaseQueue.map((item) => (
                <article key={item.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_COLORS[item.status]}`}>
                          {STATUS_LABELS[item.status]}
                        </span>
                        <span className="text-xs text-slate-500">{item.post_type === "card_news" ? "카드뉴스" : item.post_type}</span>
                      </div>
                      <h3 className="mt-2 truncate text-base font-bold text-slate-900">{item.title || "(제목 없음)"}</h3>
                      <p className="mt-1 line-clamp-2 text-sm text-slate-500">{item.text || "본문 없음"}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {item.status === "draft" ? (
                        <button
                          type="button"
                          disabled={actingId === item.id}
                          onClick={() => void requestApprovalOne(item.id)}
                          className="rounded-lg border px-3 py-2 text-xs font-semibold"
                        >
                          승인 요청
                        </button>
                      ) : null}
                      {item.status === "pending_approval" || item.status === "draft" ? (
                        <button
                          type="button"
                          disabled={actingId === item.id}
                          onClick={() => void approveOne(item.id)}
                          className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white"
                        >
                          {actingId === item.id && busy === "approve" ? "처리 중…" : "승인"}
                        </button>
                      ) : null}
                      {item.status === "approved" || item.status === "pending_approval" ? (
                        <button
                          type="button"
                          disabled={actingId === item.id}
                          onClick={() => void publishOne(item.id)}
                          className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white"
                        >
                          {actingId === item.id && busy === "publish" ? "발행 중…" : "지금 발행"}
                        </button>
                      ) : null}
                      <Link href={`/contents/${item.id}`} className="rounded-lg border px-3 py-2 text-xs font-semibold text-slate-700">
                        상세
                      </Link>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}

          <div className="mt-5 rounded-xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
            <strong className="text-slate-800">릴리즈 체크</strong>
            <ul className="mt-1 list-disc pl-5">
              <li>채널 연결·토큰이 살아 있는지 확인</li>
              <li>발행 후 `게시 ID/URL` 증거가 있는지 모니터링에서 확인</li>
              <li>예약은 캘린더에서 시간 지정 가능</li>
            </ul>
          </div>
        </StagePanel>
      ) : null}

      {/* ===== 3. 모니터링 ===== */}
      {stage === "monitor" ? (
        <StagePanel
          no={3}
          title="모니터링"
          desc="발행·예약·실패 상태를 추적하고, 실제 게시 증거가 있는지 확인합니다."
        >
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            <Metric label="발행 성공" value={publishedCount} tone="good" />
            <Metric label="게시 증거 있음" value={evidenceCount} tone="good" />
            <Metric label="실패" value={failedCount} tone={failedCount ? "bad" : "neutral"} />
          </div>

          {monitorItems.length === 0 ? (
            <Empty text="모니터링할 발행/예약 콘텐츠가 없습니다." actionLabel="2단계: 릴리즈" onAction={() => setStage("release")} />
          ) : (
            <div className="space-y-2">
              {monitorItems.map((item) => {
                const evidence = item.platform_post_id || item.published_url
                return (
                  <div key={item.id} className="rounded-xl border border-slate-200 px-4 py-3">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_COLORS[item.status]}`}>
                            {STATUS_LABELS[item.status]}
                          </span>
                          {item.status === "published" ? (
                            <span className={`text-[11px] font-semibold ${evidence ? "text-emerald-700" : "text-amber-700"}`}>
                              {evidence ? "게시 증거 OK" : "증거 없음 · 재확인"}
                            </span>
                          ) : null}
                        </div>
                        <div className="mt-1 truncate font-semibold text-slate-900">{item.title}</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {item.published_at ? `발행 ${formatTime(item.published_at)}` : item.scheduled_at ? `예약 ${formatTime(item.scheduled_at)}` : formatTime(item.updated_at)}
                          {item.publish_error ? ` · ${item.publish_error}` : ""}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {item.published_url ? (
                          <a href={item.published_url} target="_blank" rel="noreferrer" className="rounded-lg border px-3 py-2 text-xs font-semibold">
                            게시물 열기
                          </a>
                        ) : null}
                        <Link href={`/contents/${item.id}`} className="rounded-lg border px-3 py-2 text-xs font-semibold">
                          상세
                        </Link>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          <div className="mt-5 flex flex-wrap gap-2">
            <button type="button" onClick={() => setStage("comments")} className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white">
              다음: 댓글 확인
            </button>
            <Link href="/analytics" className="rounded-xl border px-4 py-2.5 text-sm font-semibold text-slate-700">
              분석 보기
            </Link>
          </div>
        </StagePanel>
      ) : null}

      {/* ===== 4. 댓글 ===== */}
      {stage === "comments" ? (
        <StagePanel
          no={4}
          title="댓글 확인 및 답글 작성"
          desc="발행된 게시물의 댓글을 수집하고, 자동 답글·수동 응대·위험 이슈 에스컬레이션을 처리합니다."
        >
          <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
              <div className="text-sm font-bold text-slate-900">댓글 동기화</div>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                인스타그램·페이스북·스레드·유튜브 중심으로 새 댓글을 가져옵니다.
                환불/고소/욕설 등은 자동 답글 없이 인박스로 넘깁니다.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={busy === "comments"}
                  onClick={() => void syncComments()}
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white disabled:opacity-40"
                >
                  {busy === "comments" ? <Loader2 size={16} className="animate-spin" /> : <MessageSquare size={16} />}
                  댓글 가져오기
                </button>
                <Link href="/inbox" className="inline-flex items-center gap-2 rounded-xl border bg-white px-4 py-3 text-sm font-semibold">
                  <Inbox size={16} /> 인박스에서 답글 작성
                </Link>
              </div>
              <p className="mt-3 text-xs text-slate-500">자동화 ON 클라이언트는 약 15분마다 백그라운드 동기화도 수행합니다.</p>
            </div>

            <div className="rounded-2xl border border-slate-100 p-4">
              <div className="mb-3 text-sm font-bold text-slate-900">최근 댓글 활동</div>
              <div className="max-h-72 space-y-2 overflow-auto">
                {commentActions.length === 0 ? (
                  <div className="rounded-lg border border-dashed px-3 py-8 text-center text-sm text-slate-400">
                    아직 댓글 활동 기록이 없습니다.
                  </div>
                ) : (
                  commentActions.map((a) => (
                    <div key={a.id} className="rounded-lg border px-3 py-2 text-sm">
                      <div className="flex justify-between gap-2">
                        <span className="font-medium">
                          {a.action === "auto_reply"
                            ? "자동 답글"
                            : a.action === "comment_escalated"
                              ? "위험 댓글 알림"
                              : "댓글 수집"}
                          {a.platform ? ` · ${a.platform}` : ""}
                        </span>
                        <span className={a.ok ? "text-emerald-600" : "text-rose-600"}>{a.ok ? "완료" : "실패"}</span>
                      </div>
                      <div className="mt-1 text-xs text-slate-500">{formatTime(a.created_at)}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="mt-5">
            <button type="button" onClick={() => setStage("spread")} className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white">
              다음: 확산
            </button>
          </div>
        </StagePanel>
      ) : null}

      {/* ===== 5. 확산 ===== */}
      {stage === "spread" ? (
        <StagePanel
          no={5}
          title="확산"
          desc="잘 된 콘텐츠를 다른 채널로 재가공하고, 해시태그·바이럴 루프로 도달을 넓힙니다."
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <SpreadCard
              title="채널 재가공"
              body="성공한 카드뉴스를 다른 채널 톤으로 다시 만들어 배포합니다."
              href="/contents/new/topic"
              cta="주제 기반 재생성"
            />
            <SpreadCard
              title="Growth · 바이럴 루프"
              body="저장·공유·댓글 참여가 일어나는 확산 설계를 확인합니다."
              href="/growth"
              cta="Growth Hub 열기"
            />
            <SpreadCard
              title="벤치마킹 참고"
              body="업계 상위 계정 패턴을 보고 다음 카드뉴스 훅을 보강합니다."
              href={selectedClientId ? `/clients/${selectedClientId}/benchmark` : "/clients"}
              cta="벤치마킹 센터"
            />
            <SpreadCard
              title="운영계획 확장"
              body="주간 채널 플랜으로 확산 일정을 묶습니다."
              href="/growth/planner"
              cta="운영계획"
            />
          </div>

          <div className="mt-5 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm leading-6 text-indigo-950">
            <strong>확산 팁</strong>
            <ul className="mt-1 list-disc pl-5">
              <li>반응 좋은 1장(훅)을 숏폼/스레드 첫 줄로 재사용</li>
              <li>댓글에서 나온 질문을 다음 카드뉴스 소재로 연결</li>
              <li>채널별 CTA를 바꿔 A/B처럼 운영</li>
            </ul>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <button type="button" onClick={() => setStage("cardnews")} className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white">
              다시 카드뉴스 만들기
            </button>
            <Link href="/analytics" className="rounded-xl border px-4 py-2.5 text-sm font-semibold">
              성과 분석
            </Link>
          </div>
        </StagePanel>
      ) : null}

      {/* Footer reminder */}
      <section className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-600">
        <span className="font-semibold text-slate-900">운영 순서:</span>{" "}
        카드뉴스 만들기 → 릴리즈 → 모니터링 → 댓글 확인/답글 → 확산
        <div className="mt-3 flex flex-wrap gap-2">
          {STAGES.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setStage(s.id)}
              className={`rounded-lg border px-2.5 py-1 text-xs font-semibold ${
                stage === s.id ? "border-indigo-300 bg-indigo-50 text-indigo-700" : "text-slate-600"
              }`}
            >
              {s.no}. {s.label}
            </button>
          ))}
        </div>
        {/* keep policies available lightly for power users */}
        {policies.some((p) => p.enabled) ? (
          <p className="mt-3 text-xs text-slate-400">
            자동화 ON 채널: {policies.filter((p) => p.enabled).map((p) => p.platform).join(", ")}
          </p>
        ) : null}
      </section>
    </div>
  )
}

function StagePanel({
  no,
  title,
  desc,
  children,
}: {
  no: number
  title: string
  desc: string
  children: ReactNode
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-xs font-bold uppercase tracking-wide text-indigo-600">{no}단계</div>
      <h2 className="mt-1 text-xl font-bold text-slate-900">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-500">{desc}</p>
      <div className="mt-5">{children}</div>
    </section>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5">
      <div className="text-[11px] text-slate-300">{label}</div>
      <div className="mt-0.5 text-lg font-bold text-white">{value}</div>
    </div>
  )
}

function Field({
  label,
  required,
  optional,
  children,
}: {
  label: string
  required?: boolean
  optional?: boolean
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-semibold text-slate-800">
        {label}
        {required ? <span className="text-rose-500"> *</span> : null}
        {optional ? <span className="font-normal text-slate-400"> (선택)</span> : null}
      </span>
      {children}
    </label>
  )
}

function Empty({
  text,
  actionLabel,
  onAction,
}: {
  text: string
  actionLabel?: string
  onAction?: () => void
}) {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center">
      <p className="text-sm text-slate-400">{text}</p>
      {actionLabel && onAction ? (
        <button type="button" onClick={onAction} className="mt-3 text-sm font-semibold text-indigo-600">
          {actionLabel}
        </button>
      ) : null}
    </div>
  )
}

function Metric({ label, value, tone }: { label: string; value: number; tone: "good" | "bad" | "neutral" }) {
  const color =
    tone === "good" ? "text-emerald-700 bg-emerald-50 border-emerald-100" : tone === "bad" ? "text-rose-700 bg-rose-50 border-rose-100" : "text-slate-700 bg-slate-50 border-slate-100"
  return (
    <div className={`rounded-xl border px-4 py-3 ${color}`}>
      <div className="text-xs font-medium opacity-80">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
    </div>
  )
}

function SpreadCard({
  title,
  body,
  href,
  cta,
}: {
  title: string
  body: string
  href: string
  cta: string
}) {
  return (
    <Link href={href} className="rounded-xl border border-slate-200 p-4 transition hover:border-indigo-300 hover:bg-indigo-50/40">
      <div className="font-bold text-slate-900">{title}</div>
      <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
      <div className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-indigo-700">
        {cta} <ArrowRight size={14} />
      </div>
    </Link>
  )
}
