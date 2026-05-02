"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { adminAISettingsService, type LLMProviderConfigItem, type LLMTaskPolicyItem } from "@/services/admin-ai-settings"

const TASK_LABELS: Record<string, { title: string; description: string }> = {
  strategy: { title: "전략/운영계획", description: "월간 전략, 주차별 주제, 채널별 운영계획 생성" },
  benchmark_analysis: { title: "벤치마킹 분석", description: "경쟁/레퍼런스 콘텐츠를 점수화하고 인사이트 추출" },
  copy_generation: { title: "카피/콘텐츠 생성", description: "제목, 설명, 본문, CTA, 해시태그 생성" },
  report_summary: { title: "리포트 요약", description: "성과 데이터 요약, 대표님 보고용 문장 생성" },
  comment_reply_draft: { title: "댓글 답변 초안", description: "댓글/DM 응대 문안 생성" },
}

const SCORE_FIELD_META: Record<
  "views_weight" | "engagement_weight" | "recency_weight" | "action_language_weight",
  { label: string; help: string }
> = {
  views_weight: { label: "조회수 비중", help: "0.45 = 최종 점수의 45%를 조회수/노출 성과로 판단" },
  engagement_weight: { label: "참여율 비중", help: "0.30 = 좋아요·댓글·저장 등 반응을 30% 반영" },
  recency_weight: { label: "최신성 비중", help: "0.15 = 최근 게시물일수록 15% 가산" },
  action_language_weight: { label: "액션문구 비중", help: "0.10 = 문의·구매·신청을 부르는 문구 패턴을 10% 반영" },
}

const modelKey = (provider: string, model: string) => `${provider}::${model}`

export default function AIEngineSettingsPage() {
  const { isAdmin, loading: authLoading } = useAuth()
  const router = useRouter()
  const [providers, setProviders] = useState<LLMProviderConfigItem[]>([])
  const [policies, setPolicies] = useState<LLMTaskPolicyItem[]>([])
  const [loading, setLoading] = useState(false)
  const [savingProviderId, setSavingProviderId] = useState<string | null>(null)
  const [savingTaskType, setSavingTaskType] = useState<string | null>(null)

  useEffect(() => {
    if (!authLoading && !isAdmin) router.push("/dashboard")
  }, [authLoading, isAdmin, router])

  const load = async () => {
    setLoading(true)
    try {
      const [providerRows, policyRows] = await Promise.all([
        adminAISettingsService.listProviders(),
        adminAISettingsService.listTaskPolicies(),
      ])
      setProviders(providerRows)
      setPolicies(policyRows)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isAdmin) void load()
  }, [isAdmin])

  const groupedProviders = useMemo(() => {
    return providers.reduce<Record<string, LLMProviderConfigItem[]>>((acc, item) => {
      acc[item.provider_name] = acc[item.provider_name] || []
      acc[item.provider_name].push(item)
      return acc
    }, {})
  }, [providers])

  const activeModelOptions = useMemo(() => {
    return [...providers].sort((a, b) => Number(b.is_active) - Number(a.is_active) || a.provider_name.localeCompare(b.provider_name) || a.model_name.localeCompare(b.model_name))
  }, [providers])

  const updatePolicy = (taskType: string, patch: Partial<LLMTaskPolicyItem>) => {
    setPolicies((prev) => prev.map((row) => (row.task_type === taskType ? { ...row, ...patch } : row)))
  }

  const applyModelSelection = (taskType: string, value: string, kind: "primary" | "fallback") => {
    const [provider, model] = value.split("::")
    if (!provider || !model) return
    if (kind === "primary") {
      updatePolicy(taskType, { primary_provider: provider, primary_model: model })
      return
    }
    updatePolicy(taskType, { fallback_provider: provider, fallback_model: model })
  }

  if (authLoading) return null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">AI 엔진 설정</h1>
        <p className="text-sm text-gray-500 mt-1">
          Task별 LLM 모델, fallback, 벤치마킹 Top-K/점수 가중치를 운영자가 바로 이해하고 조정하도록 정리했습니다.
        </p>
      </div>

      <div className="flex gap-2 border-b pb-2">
        <Link href="/settings/users" className="px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50">담당자 관리</Link>
        <Link href="/settings/secrets" className="px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50">시크릿 관리</Link>
        <Link href="/settings/ai-engine" className="px-3 py-2 rounded-lg text-sm bg-blue-50 text-blue-700 font-medium">AI 엔진 설정</Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700">
          <div className="font-semibold mb-1">추천 기본 모델</div>
          <div>GPT-5.5를 기본 고성능 모델로 사용하고, GPT-5.4 Mini는 빠른/저비용 작업에 선택합니다.</div>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 text-xs text-purple-700">
          <div className="font-semibold mb-1">Fallback</div>
          <div>기본 모델 실패·타임아웃 시 Claude 계열로 자동 우회합니다. 승인 전 외부 업로드와는 무관한 생성 라우팅 설정입니다.</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
          <div className="font-semibold mb-1">0.45 / 0.30 / 0.15 / 0.10 의미</div>
          <div>벤치마킹 후보 점수의 가중치입니다. 합계가 1.0이면 100% 기준으로 해석됩니다.</div>
        </div>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border p-6 text-sm text-gray-500">불러오는 중...</div>
      ) : (
        <>
          <div className="space-y-4">
            {Object.entries(groupedProviders).map(([providerName, rows]) => (
              <div key={providerName} className="bg-white rounded-xl border overflow-hidden">
                <div className="px-4 py-3 border-b bg-gray-50 font-semibold text-sm uppercase flex items-center justify-between">
                  <span>{providerName}</span>
                  <span className="text-xs font-normal text-gray-500">사용 가능한 모델 목록</span>
                </div>
                <div className="divide-y">
                  {rows.map((item) => (
                    <div key={item.id || `${item.provider_name}-${item.model_name}`} className="p-4 grid grid-cols-1 md:grid-cols-6 gap-3 items-center">
                      <div className="md:col-span-2">
                        <div className="font-medium text-sm">{item.label}</div>
                        <div className="text-xs text-gray-500">{item.provider_name} / {item.model_name}</div>
                      </div>
                      <label className="text-sm text-gray-600 flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={item.is_active}
                          onChange={(e) => setProviders((prev) => prev.map((row) => row.id === item.id ? { ...row, is_active: e.target.checked } : row))}
                        />
                        활성화
                      </label>
                      <label className="text-sm text-gray-600 flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={item.is_default}
                          onChange={(e) => setProviders((prev) => prev.map((row) => ({ ...row, is_default: row.id === item.id ? e.target.checked : false })))}
                        />
                        기본값
                      </label>
                      <label className="text-xs text-gray-500 space-y-1">
                        <span>타임아웃(초)</span>
                        <input
                          value={item.timeout_seconds}
                          onChange={(e) => setProviders((prev) => prev.map((row) => row.id === item.id ? { ...row, timeout_seconds: Number(e.target.value) || 60 } : row))}
                          className="w-full rounded-lg border px-3 py-2 text-sm text-gray-900"
                          aria-label="Timeout seconds"
                        />
                      </label>
                      <button
                        className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm disabled:opacity-50"
                        disabled={!item.id || savingProviderId === item.id}
                        onClick={async () => {
                          if (!item.id) return
                          try {
                            setSavingProviderId(item.id)
                            const updated = await adminAISettingsService.updateProvider(item.id, {
                              is_active: item.is_active,
                              is_default: item.is_default,
                              timeout_seconds: item.timeout_seconds,
                            })
                            setProviders((prev) => prev.map((row) => row.id === updated.id ? updated : row))
                          } finally {
                            setSavingProviderId(null)
                          }
                        }}
                      >
                        {savingProviderId === item.id ? "저장 중..." : "저장"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl border overflow-hidden">
            <div className="px-4 py-3 border-b bg-gray-50">
              <div className="font-semibold text-sm">Task별 라우팅 / K값 설정</div>
              <div className="text-xs text-gray-500 mt-1">provider와 model을 따로 입력하지 않고, LLM 모델 드롭다운 하나로 선택합니다.</div>
            </div>
            <div className="divide-y">
              {policies.map((policy) => {
                const taskMeta = TASK_LABELS[policy.task_type] || { title: policy.task_type, description: "커스텀 AI 작업" }
                const primaryValue = modelKey(policy.primary_provider, policy.primary_model)
                const fallbackValue = policy.fallback_provider && policy.fallback_model ? modelKey(policy.fallback_provider, policy.fallback_model) : ""
                const weightTotal = policy.views_weight + policy.engagement_weight + policy.recency_weight + policy.action_language_weight

                return (
                  <div key={policy.task_type} className="p-4 space-y-4">
                    <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-2">
                      <div>
                        <div className="font-semibold text-sm">{taskMeta.title}</div>
                        <div className="text-xs text-gray-500">{policy.task_type} · {taskMeta.description}</div>
                      </div>
                      <label className="text-sm text-gray-600 flex items-center gap-2">
                        <input type="checkbox" checked={policy.is_active} onChange={(e) => updatePolicy(policy.task_type, { is_active: e.target.checked })} />
                        사용
                      </label>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <label className="text-xs text-gray-500 space-y-1">
                        <span>LLM 모델</span>
                        <select
                          value={primaryValue}
                          onChange={(e) => applyModelSelection(policy.task_type, e.target.value, "primary")}
                          className="w-full rounded-lg border px-3 py-2 text-sm text-gray-900 bg-white"
                        >
                          {activeModelOptions.map((item) => (
                            <option key={modelKey(item.provider_name, item.model_name)} value={modelKey(item.provider_name, item.model_name)}>
                              {item.label} ({item.provider_name}/{item.model_name})
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="text-xs text-gray-500 space-y-1">
                        <span>Fallback 모델</span>
                        <select
                          value={fallbackValue}
                          onChange={(e) => applyModelSelection(policy.task_type, e.target.value, "fallback")}
                          className="w-full rounded-lg border px-3 py-2 text-sm text-gray-900 bg-white"
                          disabled={!policy.fallback_enabled}
                        >
                          <option value="">Fallback 없음</option>
                          {activeModelOptions.map((item) => (
                            <option key={`fallback-${modelKey(item.provider_name, item.model_name)}`} value={modelKey(item.provider_name, item.model_name)}>
                              {item.label} ({item.provider_name}/{item.model_name})
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <label className="text-xs text-gray-500 space-y-1">
                        <span>Top-K 후보 수</span>
                        <input
                          value={policy.top_k}
                          onChange={(e) => updatePolicy(policy.task_type, { top_k: Number(e.target.value) || 10 })}
                          className="w-full rounded-lg border px-3 py-2 text-sm text-gray-900"
                          aria-label="Top-K 후보 수"
                        />
                        <span className="block text-[11px] text-gray-400">예: 10 = 벤치마킹 후보 중 상위 10개 콘텐츠를 참고</span>
                      </label>
                      <label className="text-xs text-gray-500 space-y-1">
                        <span>분석 기간(일)</span>
                        <input
                          value={policy.benchmark_window_days}
                          onChange={(e) => updatePolicy(policy.task_type, { benchmark_window_days: Number(e.target.value) || 30 })}
                          className="w-full rounded-lg border px-3 py-2 text-sm text-gray-900"
                          aria-label="분석 기간"
                        />
                        <span className="block text-[11px] text-gray-400">예: 30 = 최근 30일 게시물을 우선 분석</span>
                      </label>
                    </div>

                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <div className="font-medium text-xs text-gray-700">벤치마킹 점수 가중치</div>
                          <div className="text-[11px] text-gray-500">각 숫자는 최종 점수에서 해당 항목이 차지하는 비율입니다.</div>
                        </div>
                        <div className={`text-[11px] ${Math.abs(weightTotal - 1) < 0.01 ? "text-green-700" : "text-amber-700"}`}>
                          합계 {weightTotal.toFixed(2)} / 권장 1.00
                        </div>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        {(Object.keys(SCORE_FIELD_META) as Array<keyof typeof SCORE_FIELD_META>).map((field) => (
                          <label key={field} className="text-xs text-gray-500 space-y-1">
                            <span>{SCORE_FIELD_META[field].label}</span>
                            <input
                              value={policy[field]}
                              onChange={(e) => updatePolicy(policy.task_type, { [field]: Number(e.target.value) || 0 })}
                              className="w-full rounded-lg border px-3 py-2 text-sm text-gray-900 bg-white"
                              aria-label={SCORE_FIELD_META[field].label}
                            />
                            <span className="block text-[11px] text-gray-400">{SCORE_FIELD_META[field].help}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-4">
                        <label className="text-sm text-gray-600 flex items-center gap-2">
                          <input type="checkbox" checked={policy.fallback_enabled} onChange={(e) => updatePolicy(policy.task_type, { fallback_enabled: e.target.checked })} />
                          Fallback 사용
                        </label>
                        <label className="text-sm text-gray-600 flex items-center gap-2">
                          <input type="checkbox" checked={policy.strict_json_mode} onChange={(e) => updatePolicy(policy.task_type, { strict_json_mode: e.target.checked })} />
                          JSON 엄격모드
                        </label>
                      </div>
                      <button
                        className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm disabled:opacity-50"
                        disabled={savingTaskType === policy.task_type}
                        onClick={async () => {
                          try {
                            setSavingTaskType(policy.task_type)
                            const updated = await adminAISettingsService.updateTaskPolicy(policy.task_type, policy)
                            setPolicies((prev) => prev.map((row) => row.task_type === updated.task_type ? updated : row))
                          } finally {
                            setSavingTaskType(null)
                          }
                        }}
                      >
                        {savingTaskType === policy.task_type ? "저장 중..." : "저장"}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
