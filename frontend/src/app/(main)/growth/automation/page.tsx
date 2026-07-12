"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { Bot, Loader2, MessageSquare, RefreshCw, Sparkles, ToggleLeft, ToggleRight } from "lucide-react"
import { useSelectedClient } from "@/hooks/useSelectedClient"
import {
  automationService,
  type AutomationAction,
  type AutomationPolicy,
  type AutomationRun,
  type Capability,
} from "@/services/automation"

export default function ChannelAutomationPage() {
  const { selectedClientId, selectedClient, loading: clientLoading } = useSelectedClient()
  const [policies, setPolicies] = useState<AutomationPolicy[]>([])
  const [capabilities, setCapabilities] = useState<Capability[]>([])
  const [runs, setRuns] = useState<AutomationRun[]>([])
  const [actions, setActions] = useState<AutomationAction[]>([])
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const [title, setTitle] = useState("이번 주 SNS 자동화 운영 팁")
  const [brief, setBrief] = useState("소재·예약발행·댓글 자동응답 루프를 한 번에 돌리는 방법")
  const [selectedChannels, setSelectedChannels] = useState<string[]>(["instagram", "facebook", "threads", "x"])

  const loadAll = useCallback(async () => {
    if (!selectedClientId) return
    setLoading(true)
    setErrorMessage("")
    try {
      const [caps, nextPolicies, nextRuns, nextActions] = await Promise.all([
        automationService.capabilities(),
        automationService.listPolicies(selectedClientId),
        automationService.listRuns(selectedClientId),
        automationService.listActions(selectedClientId),
      ])
      setCapabilities(caps)
      setPolicies(nextPolicies)
      setRuns(nextRuns)
      setActions(nextActions)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "자동화 데이터를 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }, [selectedClientId])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  const readyCount = useMemo(
    () => policies.filter((p) => p.enabled && p.capability?.automation_ready).length,
    [policies]
  )

  const toggleChannel = (platform: string) => {
    setSelectedChannels((prev) =>
      prev.includes(platform) ? prev.filter((p) => p !== platform) : [...prev, platform]
    )
  }

  const updatePolicy = async (policy: AutomationPolicy, patch: Partial<AutomationPolicy>) => {
    if (!selectedClientId) return
    setLoading(true)
    setErrorMessage("")
    setSuccessMessage("")
    try {
      await automationService.upsertPolicy(selectedClientId, policy.platform, {
        enabled: patch.enabled ?? policy.enabled,
        require_approval: patch.require_approval ?? policy.require_approval,
        daily_limit: patch.daily_limit ?? policy.daily_limit,
        auto_reply_enabled: patch.auto_reply_enabled ?? policy.auto_reply_enabled,
      })
      setSuccessMessage(`${policy.platform} 정책 저장됨`)
      await loadAll()
    } catch (error: unknown) {
      const detail =
        typeof error === "object" && error && "response" in error
          ? // @ts-expect-error axios shape
            error.response?.data?.detail
          : null
      setErrorMessage(String(detail || (error instanceof Error ? error.message : "정책 저장 실패")))
    } finally {
      setLoading(false)
    }
  }

  const generateMaterials = async () => {
    if (!selectedClientId) return
    setLoading(true)
    setErrorMessage("")
    setSuccessMessage("")
    try {
      const result = await automationService.generateMaterials({
        client_id: selectedClientId,
        title,
        brief,
        channels: selectedChannels,
        require_approval: true,
        generate_images: false,
        use_fallback_storyline: true,
      })
      setSuccessMessage(
        `소재 생성 ${result.ok ? "완료" : "부분 실패"} · ${result.contents.length}개 draft · topic ${result.topic_id || "-"}`
      )
      await loadAll()
    } catch (error: unknown) {
      const detail =
        typeof error === "object" && error && "response" in error
          ? // @ts-expect-error axios shape
            error.response?.data?.detail
          : null
      setErrorMessage(String(detail || (error instanceof Error ? error.message : "소재 생성 실패")))
    } finally {
      setLoading(false)
    }
  }

  const syncComments = async () => {
    if (!selectedClientId) return
    setLoading(true)
    setErrorMessage("")
    setSuccessMessage("")
    try {
      const result = await automationService.syncComments(selectedClientId)
      setSuccessMessage(
        `댓글 동기화 · 채널 ${result.synced_channels || 0} · 신규 ${result.new_comments || 0} · 자동응답 ${result.auto_replied || 0} · 에스컬레이션 ${result.escalated || 0}`
      )
      await loadAll()
    } catch (error: unknown) {
      const detail =
        typeof error === "object" && error && "response" in error
          ? // @ts-expect-error axios shape
            error.response?.data?.detail
          : null
      setErrorMessage(String(detail || (error instanceof Error ? error.message : "댓글 동기화 실패")))
    } finally {
      setLoading(false)
    }
  }

  if (clientLoading) {
    return <div className="p-8 text-sm text-gray-500">클라이언트 로딩 중…</div>
  }

  if (!selectedClientId) {
    return (
      <div className="p-8">
        <h1 className="text-xl font-bold mb-2">채널 자동화</h1>
        <p className="text-sm text-gray-500">상단에서 클라이언트를 먼저 선택하세요.</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
            <Bot size={14} /> 전 채널 오토파일럿
          </div>
          <h1 className="mt-3 text-2xl font-bold">채널 자동화</h1>
          <p className="mt-2 text-sm text-gray-500">
            {selectedClient?.name || selectedClientId} · 소재 생성 → 승인/발행 → 댓글 수집/자동응답
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadAll()}
          className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-gray-50"
        >
          <RefreshCw size={14} /> 새로고침
        </button>
      </div>

      {errorMessage ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{errorMessage}</div>
      ) : null}
      {successMessage ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{successMessage}</div>
      ) : null}

      <section className="grid gap-3 md:grid-cols-4">
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">자동화 ON</div>
          <div className="mt-1 text-2xl font-bold">{readyCount}</div>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">채널 capability</div>
          <div className="mt-1 text-2xl font-bold">{capabilities.length}</div>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">최근 run</div>
          <div className="mt-1 text-2xl font-bold">{runs.length}</div>
        </div>
        <div className="rounded-xl border bg-white p-4">
          <div className="text-xs text-gray-500">액션 로그</div>
          <div className="mt-1 text-2xl font-bold">{actions.length}</div>
        </div>
      </section>

      <section className="rounded-xl border bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">채널 정책</h2>
          <span className="text-xs text-gray-500">미지원 채널은 ON 불가</span>
        </div>
        <div className="grid gap-3">
          {policies.map((policy) => {
            const cap = policy.capability
            const ready = Boolean(cap?.automation_ready)
            return (
              <div key={policy.platform} className="rounded-lg border p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold">{cap?.label || policy.platform}</div>
                    <div className="mt-1 text-xs text-gray-500">{cap?.notes}</div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {cap?.publish ? <Badge ok label="발행" /> : <Badge ok={false} label="발행X" />}
                      {cap?.comment_fetch ? <Badge ok label="댓글수집" /> : <Badge ok={false} label="댓글X" />}
                      {cap?.comment_reply ? <Badge ok label="답글" /> : <Badge ok={false} label="답글X" />}
                      {ready ? <Badge ok label="자동화가능" /> : <Badge ok={false} label="준비안됨" />}
                    </div>
                    {(cap?.blockers || []).length > 0 ? (
                      <div className="mt-2 text-xs text-amber-700">blocker: {(cap?.blockers || []).join(" · ")}</div>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      disabled={!ready || loading}
                      onClick={() => void updatePolicy(policy, { enabled: !policy.enabled })}
                      className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm disabled:opacity-40"
                    >
                      {policy.enabled ? <ToggleRight className="text-blue-600" size={16} /> : <ToggleLeft size={16} />}
                      {policy.enabled ? "ON" : "OFF"}
                    </button>
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() => void updatePolicy(policy, { require_approval: !policy.require_approval })}
                      className="rounded-md border px-3 py-1.5 text-xs"
                    >
                      승인 {policy.require_approval ? "필요" : "생략"}
                    </button>
                    <button
                      type="button"
                      disabled={loading || !cap?.comment_fetch}
                      onClick={() => void updatePolicy(policy, { auto_reply_enabled: !policy.auto_reply_enabled })}
                      className="rounded-md border px-3 py-1.5 text-xs disabled:opacity-40"
                    >
                      자동댓글 {policy.auto_reply_enabled ? "ON" : "OFF"}
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border bg-white p-5">
          <div className="mb-4 flex items-center gap-2">
            <Sparkles size={18} className="text-blue-600" />
            <h2 className="text-lg font-semibold">소재 자동 생성</h2>
          </div>
          <div className="space-y-3">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 text-sm"
              placeholder="주제 제목"
            />
            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 text-sm min-h-[90px]"
              placeholder="브리프"
            />
            <div className="flex flex-wrap gap-2">
              {(capabilities.length ? capabilities.map((c) => c.platform) : selectedChannels).map((platform) => (
                <button
                  key={platform}
                  type="button"
                  onClick={() => toggleChannel(platform)}
                  className={`rounded-full border px-3 py-1 text-xs ${
                    selectedChannels.includes(platform) ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600"
                  }`}
                >
                  {platform}
                </button>
              ))}
            </div>
            <button
              type="button"
              disabled={loading || !title.trim() || selectedChannels.length === 0}
              onClick={() => void generateMaterials()}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              draft 생성 (fallback 스토리라인)
            </button>
            <p className="text-xs text-gray-500">생성 결과는 승인 대기 draft로 저장됩니다. `/contents`에서 확인·발행하세요.</p>
          </div>
        </div>

        <div className="rounded-xl border bg-white p-5">
          <div className="mb-4 flex items-center gap-2">
            <MessageSquare size={18} className="text-blue-600" />
            <h2 className="text-lg font-semibold">댓글 동기화 · 자동응답</h2>
          </div>
          <p className="text-sm text-gray-600">
            연결 채널 중 댓글 수집 가능한 플랫폼(현재 IG/FB/Threads/YT)을 동기화하고, 안전 규칙 기반 자동응답을 시도합니다.
            위험 키워드(환불/고소/욕설 등)는 자동응답하지 않고 에스컬레이션 로그로 남깁니다.
          </p>
          <button
            type="button"
            disabled={loading}
            onClick={() => void syncComments()}
            className="mt-4 inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 disabled:opacity-40"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <MessageSquare size={14} />}
            지금 댓글 동기화
          </button>
          <p className="mt-3 text-xs text-gray-500">스케줄러도 15분마다 자동화 ON 클라이언트를 백그라운드 동기화합니다.</p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border bg-white p-5">
          <h2 className="mb-3 text-lg font-semibold">최근 Run</h2>
          <div className="space-y-2 max-h-80 overflow-auto">
            {runs.length === 0 ? <Empty text="실행 이력 없음" /> : null}
            {runs.map((run) => (
              <div key={run.id} className="rounded-md border px-3 py-2 text-sm">
                <div className="flex justify-between gap-2">
                  <span className="font-medium">{run.kind}</span>
                  <span className={run.status === "ok" ? "text-emerald-600" : "text-amber-700"}>{run.status}</span>
                </div>
                <div className="mt-1 text-xs text-gray-500">{run.started_at}</div>
                {run.error ? <div className="mt-1 text-xs text-rose-600">{run.error}</div> : null}
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <h2 className="mb-3 text-lg font-semibold">액션 로그</h2>
          <div className="space-y-2 max-h-80 overflow-auto">
            {actions.length === 0 ? <Empty text="액션 로그 없음" /> : null}
            {actions.map((action) => (
              <div key={action.id} className="rounded-md border px-3 py-2 text-sm">
                <div className="flex justify-between gap-2">
                  <span className="font-medium">
                    {action.action}
                    {action.platform ? ` · ${action.platform}` : ""}
                  </span>
                  <span className={action.ok ? "text-emerald-600" : "text-rose-600"}>{action.ok ? "ok" : "fail"}</span>
                </div>
                {action.error ? <div className="mt-1 text-xs text-rose-600">{action.error}</div> : null}
                <div className="mt-1 text-xs text-gray-500">{action.created_at}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
        ok ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-gray-50 text-gray-500 border border-gray-200"
      }`}
    >
      {label}
    </span>
  )
}

function Empty({ text }: { text: string }) {
  return <div className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-gray-400">{text}</div>
}
