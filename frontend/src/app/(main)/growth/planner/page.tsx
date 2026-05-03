"use client"

import { useEffect, useMemo, useState } from "react"
import { AlertTriangle, CalendarDays, CheckCircle2, ClipboardList, Loader2, Sparkles, Target, UploadCloud } from "lucide-react"
import { aiService, type GenerateOperationPlanPayload, type GenerateOperationPlanResponse } from "@/services/ai"
import { operationPlansService, type OperationPlanDraftsResponse, type OperationPlanRecord } from "@/services/operation-plans"
import { useSelectedClient } from "@/hooks/useSelectedClient"

const CHANNEL_OPTIONS = ["instagram", "threads", "blog", "youtube", "tiktok", "facebook", "kakao", "linkedin", "x"]

function splitList(value: string) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function defaultMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
}

export default function OperationPlannerPage() {
  const [brandName, setBrandName] = useState("")
  const [productSummary, setProductSummary] = useState("")
  const [targetAudience, setTargetAudience] = useState("")
  const [goalsText, setGoalsText] = useState("인지도 확보, 문의 확보")
  const [benchmarkText, setBenchmarkText] = useState("")
  const [channels, setChannels] = useState<string[]>(["instagram", "threads", "blog"])
  const [month, setMonth] = useState(defaultMonth())
  const [seasonContext, setSeasonContext] = useState("")
  const [notes, setNotes] = useState("")
  const [plan, setPlan] = useState<GenerateOperationPlanResponse | null>(null)
  const [lastRequest, setLastRequest] = useState<GenerateOperationPlanPayload | null>(null)
  const [savedPlan, setSavedPlan] = useState<OperationPlanRecord | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [draftLoading, setDraftLoading] = useState(false)
  const [draftResult, setDraftResult] = useState<OperationPlanDraftsResponse | null>(null)
  const [actionLoading, setActionLoading] = useState<"submit" | "approve" | "reject" | null>(null)
  const [recovering, setRecovering] = useState(false)
  const [restoring, setRestoring] = useState(true)
  const [error, setError] = useState("")
  const [statusMessage, setStatusMessage] = useState("")
  const { selectedClientId, selectedClient, loading: clientLoading } = useSelectedClient()

  const canSubmit = useMemo(() => brandName.trim() && productSummary.trim() && channels.length > 0, [brandName, productSummary, channels])

  useEffect(() => {
    if (clientLoading) return
    let cancelled = false

    async function restoreLatestPlan() {
      setRestoring(true)
      try {
        const response = await operationPlansService.list(selectedClientId ? { client_id: selectedClientId } : undefined)
        let latest = Array.isArray(response.items) ? response.items.find((item) => item.plan_payload) : null

        if (!latest && selectedClientId) {
          const fallback = await operationPlansService.list()
          latest = Array.isArray(fallback.items) ? fallback.items.find((item) => item.plan_payload) : null
        }

        if (cancelled || !latest?.plan_payload) return

        const request = latest.request_payload
        setPlan(latest.plan_payload)
        setSavedPlan(latest)
        setLastRequest(request)
        setDraftResult(null)
        setBrandName(latest.plan_payload.brand_name || latest.brand_name || "")
        setMonth(latest.plan_payload.month || latest.month || defaultMonth())
        if (request) {
          setProductSummary(request.product_summary || "")
          setTargetAudience(request.target_audience || "")
          setGoalsText((request.goals || []).join(", "))
          setBenchmarkText((request.benchmark_brands || []).join(", "))
          setChannels(request.channels?.length ? request.channels : ["instagram", "threads", "blog"])
          setSeasonContext(request.season_context || "")
          setNotes(request.notes || "")
        }
        setStatusMessage(`최근 저장 운영계획을 복구했습니다: ${latest.brand_name} ${latest.month} · ${latest.status}`)
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "최근 운영계획 복구에 실패했습니다."
          setError(message)
        }
      } finally {
        if (!cancelled) setRestoring(false)
      }
    }

    restoreLatestPlan()
    return () => {
      cancelled = true
    }
  }, [clientLoading, selectedClientId])

  function toggleChannel(channel: string) {
    setChannels((prev) => prev.includes(channel) ? prev.filter((item) => item !== channel) : [...prev, channel])
  }

  async function generatePlan() {
    if (!canSubmit) return
    const requestPayload: GenerateOperationPlanPayload = {
      brand_name: brandName,
      product_summary: productSummary,
      target_audience: targetAudience,
      goals: splitList(goalsText),
      channels,
      benchmark_brands: splitList(benchmarkText),
      month,
      season_context: seasonContext,
      notes,
    }
    setLoading(true)
    setError("")
    setStatusMessage("")
    try {
      const result = await aiService.generateOperationPlan(requestPayload)
      setLastRequest(requestPayload)
      setPlan(result)
      setSavedPlan(null)
      setDraftResult(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : "운영계획 생성에 실패했습니다."
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  async function savePlan() {
    if (!plan || !lastRequest) return
    if (!selectedClientId) {
      setError("운영계획 저장 전에 상단에서 클라이언트를 선택해주세요. 선택 없이 저장하면 실행 단계에서 콘텐츠가 생성되지 않습니다.")
      return
    }
    setSaving(true)
    setError("")
    setStatusMessage("운영계획 저장 중입니다...")
    try {
      const saved = await operationPlansService.create({
        client_id: selectedClientId,
        brand_name: plan.brand_name,
        month: plan.month,
        strategy_summary: plan.strategy_summary,
        request_payload: lastRequest,
        plan_payload: plan,
      })
      setSavedPlan(saved)
      setDraftResult(null)
      setStatusMessage("운영계획을 draft 상태로 저장했습니다.")
    } catch (err) {
      const message = err instanceof Error ? err.message : "운영계획 저장에 실패했습니다."
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  async function runPlanAction(action: "submit" | "approve" | "reject") {
    if (!savedPlan) return
    setActionLoading(action)
    setError("")
    setStatusMessage(action === "submit" ? "승인 요청 처리 중입니다..." : action === "approve" ? "운영계획 승인 처리 중입니다..." : "반려 처리 중입니다...")
    try {
      const memo = action === "submit" ? "대표님 승인 요청" : action === "approve" ? "운영계획 승인" : "수정 필요"
      const updated = await operationPlansService[action](savedPlan.id, memo)
      setSavedPlan(updated)
      setDraftResult(null)
      setStatusMessage(action === "submit" ? "승인 요청 상태로 전환했습니다." : action === "approve" ? "운영계획을 승인했습니다." : "운영계획을 반려했습니다.")
    } catch (err) {
      const message = err instanceof Error ? err.message : "상태 변경에 실패했습니다."
      setError(message)
    } finally {
      setActionLoading(null)
    }
  }

  async function generateDrafts() {
    if (!savedPlan) return
    let executablePlan = savedPlan
    if (!executablePlan.client_id) {
      if (!selectedClientId) {
        setError("콘텐츠 draft 생성 전에 상단 클라이언트를 선택해주세요. 현재 운영계획에 client_id가 없어 실행할 수 없습니다.")
        return
      }
      setRecovering(true)
      setError("")
      setStatusMessage("저장된 운영계획을 현재 클라이언트와 연결 중입니다...")
      try {
        executablePlan = await operationPlansService.update(executablePlan.id, { client_id: selectedClientId })
        setSavedPlan(executablePlan)
      } catch (err) {
        const message = err instanceof Error ? err.message : "운영계획 클라이언트 연결 복구에 실패했습니다."
        setError(message)
        setRecovering(false)
        return
      }
      setRecovering(false)
    }

    setDraftLoading(true)
    setError("")
    setStatusMessage("콘텐츠 draft를 생성 중입니다... 페이지를 이동해도 저장된 운영계획에서 복구됩니다.")
    try {
      const result = await operationPlansService.generateDrafts(executablePlan.id)
      setDraftResult(result)
      setStatusMessage(`콘텐츠 draft ${result.total}개 생성 완료 — 예약 전 토큰확인 ${result.token_check_required_count}개, 수동필요 ${result.manual_required_count}개`)
    } catch (err) {
      const message = err instanceof Error ? err.message : "콘텐츠 draft 생성에 실패했습니다. client_id 연결/승인 상태를 확인해주세요."
      setError(message)
    } finally {
      setDraftLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-full">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-blue-600">Mega Autonomous SNS Ops</p>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">브랜드 운영계획 생성</h1>
          <p className="text-sm text-gray-500 mt-2">브랜드·상품·벤치마킹·시즌을 넣으면 월간 제작 수량과 채널별 콘텐츠 계획을 만듭니다.</p>
        </div>
        <div className="rounded-2xl border bg-white px-4 py-3 text-xs text-gray-600 max-w-xs">
          <div className="flex items-center gap-2 font-semibold text-gray-800 mb-1"><CheckCircle2 size={14} className="text-green-600" /> 승인 우선 모드</div>
          <p>컨펌 전에는 업로드하지 않고, 계획·리스크·필요자료를 먼저 분리합니다.</p>
          <p className="mt-2 text-blue-700 font-semibold">현재 클라이언트: {clientLoading ? "확인 중..." : selectedClient?.name || "미선택"}</p>
        </div>
      </div>

      <div className="grid xl:grid-cols-[420px_1fr] gap-6 items-start">
        <section className="bg-white border rounded-2xl p-5 space-y-4 shadow-sm">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">브랜드명 *</label>
            <input value={brandName} onChange={(e) => setBrandName(e.target.value)} placeholder="예: 아임탑, 메가커피, 병원 브랜드" className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">상품/서비스 설명 *</label>
            <textarea value={productSummary} onChange={(e) => setProductSummary(e.target.value)} rows={4} placeholder="무엇을 팔고, 어떤 차별점이 있는지 적어주세요." className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">타겟 고객</label>
            <input value={targetAudience} onChange={(e) => setTargetAudience(e.target.value)} placeholder="예: 30~45세 직장인 여성, 병원 마케팅 담당자" className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">목표</label>
            <input value={goalsText} onChange={(e) => setGoalsText(e.target.value)} placeholder="인지도 확보, 문의 확보, 구매 전환" className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <p className="text-xs text-gray-400 mt-1">쉼표 또는 줄바꿈으로 여러 개 입력</p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">운영 채널</label>
            <div className="flex flex-wrap gap-2">
              {CHANNEL_OPTIONS.map((channel) => (
                <button key={channel} type="button" onClick={() => toggleChannel(channel)} className={`px-3 py-1.5 rounded-full text-xs border transition ${channels.includes(channel) ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 hover:border-blue-300"}`}>
                  {channel}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">벤치마킹 브랜드/계정</label>
            <textarea value={benchmarkText} onChange={(e) => setBenchmarkText(e.target.value)} rows={3} placeholder="예: 스타벅스, HubSpot, @competitor" className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">운영 월</label>
              <input value={month} onChange={(e) => setMonth(e.target.value)} placeholder="2026-06" className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">시즌 맥락</label>
              <input value={seasonContext} onChange={(e) => setSeasonContext(e.target.value)} placeholder="초여름, 장마, 연말" className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">추가 메모</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="금지 표현, 필수 메시지, 운영 리소스 등" className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          {error && <div className="rounded-xl bg-red-50 text-red-700 text-sm p-3">{error}</div>}
          {statusMessage && <div className="rounded-xl bg-green-50 text-green-700 text-sm p-3 flex items-center gap-2">{(loading || saving || actionLoading || draftLoading || recovering || restoring) && <Loader2 size={14} className="animate-spin" />}<span>{statusMessage}</span></div>}

          <button onClick={generatePlan} disabled={!canSubmit || loading || saving || actionLoading !== null || draftLoading || recovering} className="w-full rounded-xl bg-blue-600 text-white py-3 text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {loading ? "메가가 운영계획 생성 중..." : "월간 운영계획 생성"}
          </button>
        </section>

        <section className="space-y-5">
          {!plan && (
            <div className="bg-white border rounded-2xl p-8 text-center text-gray-500 shadow-sm">
              <ClipboardList className="mx-auto text-blue-500 mb-3" size={36} />
              <p className="font-semibold text-gray-800">브랜드 브리프를 입력하면 월간 운영계획이 여기에 표시됩니다.</p>
              <p className="text-sm mt-2">채널별 수량, 주차별 테마, 승인 체크리스트까지 한 번에 생성합니다.</p>
            </div>
          )}

          {plan && (
            <>
              <div className="bg-white border rounded-2xl p-5 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{plan.brand_name} {plan.month} 운영계획</h2>
                    <p className="text-sm text-gray-600 mt-2">{plan.strategy_summary}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span className="px-3 py-1 rounded-full bg-amber-50 text-amber-700 text-xs font-semibold">{plan.benchmark_source_status}</span>
                    {savedPlan && <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-xs font-semibold">저장상태: {savedPlan.status}</span>}
                    {savedPlan && !savedPlan.client_id && <span className="px-3 py-1 rounded-full bg-red-50 text-red-700 text-xs font-semibold">클라이언트 연결 필요</span>}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 mt-5">
                  {savedPlan && (
                    <div className="basis-full rounded-xl bg-blue-50 text-blue-800 text-xs p-3">
                      저장된 운영계획 ID: <span className="font-mono">{savedPlan.id}</span> · 다른 메뉴로 이동해도 이 화면 진입 시 DB에서 다시 불러옵니다.
                    </div>
                  )}
                  {savedPlan && !savedPlan.client_id && selectedClientId && (
                    <div className="basis-full rounded-xl bg-amber-50 text-amber-800 text-xs p-3">
                      이 운영계획은 이전 버전에서 클라이언트 없이 저장됐습니다. 콘텐츠 draft 생성 시 현재 클라이언트({selectedClient?.name || selectedClientId})로 자동 복구합니다.
                    </div>
                  )}
                  <button type="button" onClick={savePlan} disabled={saving || Boolean(savedPlan) || clientLoading} className="rounded-xl bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-black disabled:opacity-50 flex items-center gap-2">
                    {saving && <Loader2 size={14} className="animate-spin" />}
                    {savedPlan ? "저장됨" : "운영계획 저장"}
                  </button>
                  <button type="button" onClick={() => runPlanAction("submit")} disabled={!savedPlan || savedPlan.status !== "draft" || actionLoading !== null || draftLoading || recovering} className="rounded-xl bg-blue-600 text-white px-4 py-2 text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2">
                    {actionLoading === "submit" && <Loader2 size={14} className="animate-spin" />}
                    {actionLoading === "submit" ? "승인 요청 중..." : "승인 요청"}
                  </button>
                  <button type="button" onClick={() => runPlanAction("approve")} disabled={!savedPlan || savedPlan.status !== "pending_approval" || actionLoading !== null || draftLoading || recovering} className="rounded-xl bg-green-600 text-white px-4 py-2 text-sm font-semibold hover:bg-green-700 disabled:opacity-50 flex items-center gap-2">
                    {actionLoading === "approve" && <Loader2 size={14} className="animate-spin" />}
                    {actionLoading === "approve" ? "승인 중..." : "승인"}
                  </button>
                  <button type="button" onClick={() => runPlanAction("reject")} disabled={!savedPlan || savedPlan.status !== "pending_approval" || actionLoading !== null || draftLoading || recovering} className="rounded-xl border border-red-200 text-red-700 px-4 py-2 text-sm font-semibold hover:bg-red-50 disabled:opacity-50 flex items-center gap-2">
                    {actionLoading === "reject" && <Loader2 size={14} className="animate-spin" />}
                    {actionLoading === "reject" ? "반려 중..." : "반려"}
                  </button>
                  <button type="button" onClick={generateDrafts} disabled={!savedPlan || savedPlan.status !== "approved" || draftLoading || recovering || Boolean(draftResult)} className="rounded-xl bg-purple-600 text-white px-4 py-2 text-sm font-semibold hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2">
                    {draftLoading || recovering ? <Loader2 size={14} className="animate-spin" /> : <UploadCloud size={14} />}
                    {recovering ? "클라이언트 연결 중..." : draftLoading ? "draft 생성 중..." : draftResult ? "draft 생성됨" : "콘텐츠 draft 생성"}
                  </button>
                </div>
                {draftResult && (
                  <div className="mt-4 rounded-xl border border-purple-100 bg-purple-50 p-4 text-sm text-purple-900">
                    <p className="font-semibold">콘텐츠 draft {draftResult.total}개 생성</p>
                    <p className="mt-1">예약 전 토큰 확인 필요: {draftResult.token_check_required_count}개 · 수동 필요: {draftResult.manual_required_count}개</p>
                    <p className="mt-1 text-purple-700">외부 업로드/예약은 아직 실행하지 않았고, 각 콘텐츠별 승인 이후에만 진행합니다.</p>
                  </div>
                )}
                <div className="grid sm:grid-cols-3 gap-3 mt-5">
                  <div className="rounded-xl bg-blue-50 p-4">
                    <p className="text-xs text-blue-600 font-semibold">총 제작량</p>
                    <p className="text-2xl font-bold text-blue-900 mt-1">{plan.total_monthly_count}개</p>
                  </div>
                  <div className="rounded-xl bg-purple-50 p-4">
                    <p className="text-xs text-purple-600 font-semibold">운영 채널</p>
                    <p className="text-2xl font-bold text-purple-900 mt-1">{plan.channel_plan.length}개</p>
                  </div>
                  <div className="rounded-xl bg-green-50 p-4">
                    <p className="text-xs text-green-600 font-semibold">운영 월</p>
                    <p className="text-2xl font-bold text-green-900 mt-1">{plan.month}</p>
                  </div>
                </div>
              </div>

              <div className="grid lg:grid-cols-2 gap-5">
                <InfoList title="타겟 인사이트" icon={<Target size={16} />} items={plan.target_insights} />
                <InfoList title="상품성 앵글" icon={<Sparkles size={16} />} items={plan.product_angles} />
              </div>

              {(plan.supermarketing_strategy || []).length > 0 && (
                <InfoList title="슈퍼마케팅 전략 판단" icon={<Sparkles size={16} />} items={plan.supermarketing_strategy} tone="green" />
              )}

              <div className="bg-white border rounded-2xl p-5 shadow-sm">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2"><CalendarDays size={16} /> 채널별 제작 수량</h3>
                <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
                  {plan.channel_plan.map((channel) => (
                    <div key={channel.channel} className="rounded-xl border p-4 bg-gray-50">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-semibold text-gray-900">{channel.channel}</p>
                        <span className="text-sm font-bold text-blue-700">{channel.monthly_count}개</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">{channel.role}</p>
                      <p className="text-xs text-gray-600 mt-2">{channel.cadence}</p>
                      <div className="flex flex-wrap gap-1 mt-3">
                        {channel.recommended_formats.map((format) => <span key={format} className="px-2 py-1 bg-white border rounded-full text-[11px] text-gray-600">{format}</span>)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white border rounded-2xl p-5 shadow-sm">
                <h3 className="font-bold text-gray-900 mb-4">주차별 운영계획</h3>
                <div className="space-y-3">
                  {plan.weekly_plan.map((week) => (
                    <div key={week.week} className="rounded-xl border p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold text-blue-600">Week {week.week}</p>
                          <p className="font-semibold text-gray-900 mt-1">{week.theme}</p>
                          <p className="text-xs text-gray-500 mt-1">목표: {week.objective}</p>
                        </div>
                      </div>
                      <div className="grid sm:grid-cols-2 gap-2 mt-3">
                        {week.channels.map((channel) => (
                          <div key={`${week.week}-${channel.channel}`} className="rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
                            <span className="font-semibold text-gray-800">{channel.channel}</span> · {channel.count}개 · {channel.formats.join(", ")}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid lg:grid-cols-2 gap-5">
                <InfoList title="승인 체크리스트" icon={<CheckCircle2 size={16} />} items={plan.approval_checklist} />
                <InfoList title="리스크/확인 필요" icon={<AlertTriangle size={16} />} items={plan.risks} tone="amber" />
                <InfoList title="벤치마킹 메모" icon={<ClipboardList size={16} />} items={plan.benchmark_notes} />
                <InfoList title="컨펌 후 다음 액션" icon={<UploadCloud size={16} />} items={plan.next_actions} tone="green" />
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}

function InfoList({ title, icon, items, tone = "blue" }: { title: string; icon: React.ReactNode; items: string[]; tone?: "blue" | "amber" | "green" }) {
  const color = tone === "amber" ? "text-amber-700 bg-amber-50" : tone === "green" ? "text-green-700 bg-green-50" : "text-blue-700 bg-blue-50"
  return (
    <div className="bg-white border rounded-2xl p-5 shadow-sm">
      <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">{icon} {title}</h3>
      <ul className="space-y-2">
        {(items || []).map((item, index) => (
          <li key={`${title}-${index}`} className="flex items-start gap-2 text-sm text-gray-700">
            <span className={`mt-0.5 shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${color}`}>{index + 1}</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
