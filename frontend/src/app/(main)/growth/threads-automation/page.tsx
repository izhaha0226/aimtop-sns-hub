"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import { BadgeCheck, Bot, CheckCircle2, ClipboardList, History, MessageCircle, ShieldAlert, Target, ThumbsUp, XCircle } from "lucide-react"
import { useSelectedClient } from "@/hooks/useSelectedClient"
import {
  threadsAutomationService,
} from "@/services/threadsAutomation"
import type {
  AuthIdentity,
  ThreadsActionLog,
  ThreadsApproval,
  ThreadsDraft,
  ThreadsLearningEvent,
  ThreadsPersona,
  ThreadsTargetRule,
} from "@/services/threadsAutomation"

const splitTerms = (value: string) => value.split(",").map(item => item.trim()).filter(Boolean)
const percent = (value: number) => `${Math.round(value * 100)}%`

export default function ThreadsAutomationPage() {
  const { selectedClientId, selectedClient, loading: clientLoading } = useSelectedClient()
  const [personas, setPersonas] = useState<ThreadsPersona[]>([])
  const [rules, setRules] = useState<ThreadsTargetRule[]>([])
  const [drafts, setDrafts] = useState<ThreadsDraft[]>([])
  const [approvals, setApprovals] = useState<ThreadsApproval[]>([])
  const [actions, setActions] = useState<ThreadsActionLog[]>([])
  const [learning, setLearning] = useState<ThreadsLearningEvent[]>([])
  const [identities, setIdentities] = useState<AuthIdentity[]>([])
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState("")
  const [personaName, setPersonaName] = useState("관계형 댓글 페르소나")
  const [keywords, setKeywords] = useState("AI, 자동화, 마케팅")
  const [targetText, setTargetText] = useState("Threads에서 AI 자동화와 마케팅 운영을 고민하는 게시글")
  const [draftText, setDraftText] = useState("좋은 관점입니다. 실제 운영에서는 승인 큐와 안전 필터를 먼저 두는 방식이 안정적이었습니다.")

  const loadAll = useCallback(async () => {
    if (!selectedClientId) return
    setLoading(true)
    setErrorMessage("")
    try {
      const [nextPersonas, nextRules, nextDrafts, nextApprovals, nextActions, nextLearning, nextIdentities] = await Promise.all([
        threadsAutomationService.listPersonas(selectedClientId),
        threadsAutomationService.listTargetRules(selectedClientId),
        threadsAutomationService.listDrafts(selectedClientId),
        threadsAutomationService.listApprovals(selectedClientId),
        threadsAutomationService.listActions(selectedClientId),
        threadsAutomationService.listLearning(selectedClientId),
        threadsAutomationService.listAuthIdentities(selectedClientId),
      ])
      setPersonas(nextPersonas)
      setRules(nextRules)
      setDrafts(nextDrafts)
      setApprovals(nextApprovals)
      setActions(nextActions)
      setLearning(nextLearning)
      setIdentities(nextIdentities)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Threads 자동화 데이터를 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }, [selectedClientId])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const activePersona = personas[0]
  const activeRule = rules[0]
  const providerBadges = useMemo(() => {
    const providers = identities.map(identity => `${identity.provider} ${identity.badge_label}`)
    return providers.length ? providers : ["Discord 인증 준비", "Google 인증 준비", "GitHub 인증 준비"]
  }, [identities])

  const run = async (fn: () => Promise<void>) => {
    setLoading(true)
    setErrorMessage("")
    try {
      await fn()
      await loadAll()
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "요청 처리 중 오류가 발생했습니다.")
      setLoading(false)
    }
  }

  if (clientLoading) return <div className="p-6 text-sm text-gray-500">클라이언트 정보를 불러오는 중...</div>

  if (!selectedClientId) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Threads 관계형 자동화</h1>
        <div className="mt-4 rounded-lg border bg-white p-5 text-sm text-gray-600">먼저 상단에서 클라이언트를 선택해주세요.</div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-amber-700">
            <ShieldAlert size={16} /> 실제 Threads write 비활성, 승인 큐만 생성
          </div>
          <h1 className="mt-2 text-2xl font-bold">Threads 관계형 자동화</h1>
          <p className="mt-1 text-sm text-gray-500">{selectedClient?.name || "선택 클라이언트"}의 타깃 글에 좋아요와 승인형 댓글로 관계를 만듭니다.</p>
        </div>
        <button onClick={loadAll} disabled={loading} className="rounded-lg border bg-white px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50">
          새로고침
        </button>
      </div>

      {errorMessage && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{errorMessage}</div>}

      <div className="grid gap-3 md:grid-cols-4">
        <Metric icon={Bot} label="AI 초안" value={`${drafts.length}`} />
        <Metric icon={ClipboardList} label="사람 승인" value={`${approvals.filter(item => item.status === "queued").length}`} />
        <Metric icon={ThumbsUp} label="자동화 큐 발행" value={`${actions.filter(item => item.status === "queued").length}`} />
        <Metric icon={BadgeCheck} label="Provider badge" value={`${identities.length || 3}`} />
      </div>

      <section className="grid gap-5 xl:grid-cols-2">
        <div className="rounded-lg border bg-white p-5">
          <h2 className="flex items-center gap-2 font-semibold"><Bot size={17} /> Persona Profile</h2>
          <div className="mt-4 grid gap-3">
            <input value={personaName} onChange={event => setPersonaName(event.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
            <input value={keywords} onChange={event => setKeywords(event.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
            <button
              disabled={loading}
              onClick={() => run(async () => {
                await threadsAutomationService.createPersona({
                  client_id: selectedClientId,
                  name: personaName,
                  tone_keywords_json: splitTerms(keywords),
                  author_display_name: selectedClient?.name || "SNS Hub Operator",
                  author_transparency: "AI가 초안을 만들고 사람이 승인합니다.",
                  provider_badge_label: "Discord 인증됨",
                })
              })}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Persona 저장
            </button>
          </div>
          <List items={personas.map(item => `${item.name} · ${item.provider_badge_label || "badge 없음"} · ${item.author_transparency || "투명성 문구 없음"}`)} />
        </div>

        <div className="rounded-lg border bg-white p-5">
          <h2 className="flex items-center gap-2 font-semibold"><Target size={17} /> Target Discovery Rule</h2>
          <div className="mt-4 grid gap-3">
            <input value={keywords} onChange={event => setKeywords(event.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
            <button
              disabled={loading}
              onClick={() => run(async () => {
                await threadsAutomationService.createTargetRule({
                  client_id: selectedClientId,
                  name: "키워드+경쟁계정 혼합 룰",
                  keywords_json: splitTerms(keywords),
                  hashtags_json: splitTerms(keywords).map(item => `#${item.replace(/^#/, "")}`),
                  competitor_handles_json: ["@reference_brand"],
                  min_fit_score: 0.55,
                  auto_like_enabled: true,
                  requires_comment_approval: true,
                })
              })}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Rule 저장
            </button>
          </div>
          <List items={rules.map(item => `${item.name} · 좋아요 ${item.daily_like_limit}/일 · 댓글 ${item.daily_comment_limit}/일 · 승인 ${item.requires_comment_approval ? "필수" : "선택"}`)} />
        </div>
      </section>

      <section className="rounded-lg border bg-white p-5">
        <h2 className="flex items-center gap-2 font-semibold"><MessageCircle size={17} /> Draft Board</h2>
        <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_1fr_auto]">
          <input value={targetText} onChange={event => setTargetText(event.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
          <input value={draftText} onChange={event => setDraftText(event.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
          <button
            disabled={loading}
            onClick={() => run(async () => {
              await threadsAutomationService.createDraft({
                client_id: selectedClientId,
                persona_id: activePersona?.id,
                target_rule_id: activeRule?.id,
                action_type: "comment",
                target_author_handle: "@target_author",
                target_post_text: targetText,
                draft_text: draftText,
              })
            })}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            AI 초안 생성
          </button>
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {drafts.map(draft => (
            <div key={draft.id} className="rounded-lg border p-4">
              <div className="flex items-center justify-between gap-2 text-xs text-gray-500">
                <span>{draft.action_type}</span>
                <span>{draft.status}</span>
              </div>
              <p className="mt-2 text-sm text-gray-800">{draft.draft_text || "좋아요 액션"}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <Pill>적합도 {percent(draft.fit_score)}</Pill>
                <Pill>안전 {percent(draft.safety_score)}</Pill>
                <Pill>{draft.approval_required ? "사람 승인" : "자동화 큐 발행"}</Pill>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-3">
        <Panel title="Approval Queue" icon={ClipboardList}>
          {approvals.map(item => (
            <div key={item.id} className="rounded-lg border p-3 text-sm">
              <div className="font-medium">{item.action_type} · {item.status}</div>
              <p className="mt-1 text-xs text-gray-500">{item.queue_reason}</p>
              <div className="mt-3 flex gap-2">
                <IconButton label="승인" icon={CheckCircle2} onClick={() => run(() => threadsAutomationService.updateApproval(item.id, "approved", "사람 승인 완료").then())} />
                <IconButton label="거절" icon={XCircle} onClick={() => run(() => threadsAutomationService.updateApproval(item.id, "rejected", "승인자 거절").then())} />
              </div>
            </div>
          ))}
        </Panel>

        <Panel title="Action Log" icon={History}>
          <button
            disabled={loading}
            onClick={() => run(async () => {
              const firstApproval = approvals.find(item => item.status === "approved") || approvals[0]
              await threadsAutomationService.createAction({
                client_id: selectedClientId,
                draft_id: drafts[0]?.id,
                approval_id: firstApproval?.id,
                action_type: firstApproval?.action_type || "like",
              })
            })}
            className="rounded-lg border px-3 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            시뮬레이션 실행 기록
          </button>
          {actions.map(item => <div key={item.id} className="rounded-lg bg-gray-50 p-3 text-sm">{item.action_type} · {item.status}<br /><span className="text-xs text-gray-500">{item.message}</span></div>)}
        </Panel>

        <Panel title="Performance Learning" icon={BadgeCheck}>
          <button
            disabled={loading}
            onClick={() => run(async () => {
              await threadsAutomationService.createLearning({
                client_id: selectedClientId,
                action_log_id: actions[0]?.id,
                event_type: "approval_feedback",
                signal_score: 0.8,
                outcome: "approved_pattern",
                notes: "승인된 댓글 톤을 다음 초안에 반영",
              })
            })}
            className="rounded-lg border px-3 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            학습 이벤트 기록
          </button>
          {learning.map(item => <div key={item.id} className="rounded-lg bg-gray-50 p-3 text-sm">{item.event_type} · {percent(item.signal_score)}<br /><span className="text-xs text-gray-500">{item.notes}</span></div>)}
        </Panel>
      </section>

      <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-amber-900"><ShieldAlert size={16} /> 인증 badge와 실행 제한</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {providerBadges.map(item => <Pill key={item}>{item}</Pill>)}
          <Pill>token 저장 금지</Pill>
          <Pill>external_write_enabled=false</Pill>
          <Pill>승인 큐 중심 MVP</Pill>
        </div>
      </section>
    </div>
  )
}

function Metric({ icon: Icon, label, value }: { icon: typeof Bot; label: string; value: string }) {
  return <div className="rounded-lg border bg-white p-4"><div className="flex items-center gap-2 text-sm text-gray-500"><Icon size={16} /> {label}</div><div className="mt-2 text-2xl font-bold">{value}</div></div>
}

function Panel({ title, icon: Icon, children }: { title: string; icon: typeof Bot; children: ReactNode }) {
  return <div className="space-y-3 rounded-lg border bg-white p-5"><h2 className="flex items-center gap-2 font-semibold"><Icon size={17} /> {title}</h2>{children}</div>
}

function Pill({ children }: { children: ReactNode }) {
  return <span className="rounded-full bg-white px-2 py-1 text-xs font-medium text-gray-700 ring-1 ring-gray-200">{children}</span>
}

function List({ items }: { items: string[] }) {
  return <div className="mt-4 space-y-2">{items.length ? items.map(item => <div key={item} className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700">{item}</div>) : <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-500">아직 저장된 항목이 없습니다.</div>}</div>
}

function IconButton({ label, icon: Icon, onClick }: { label: string; icon: typeof CheckCircle2; onClick: () => void }) {
  return <button onClick={onClick} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-gray-50"><Icon size={14} /> {label}</button>
}
