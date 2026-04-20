"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { adminAISettingsService, type LLMProviderConfigItem, type LLMTaskPolicyItem } from "@/services/admin-ai-settings"

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

  if (authLoading) return null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">AI 엔진 설정</h1>
        <p className="text-sm text-gray-500 mt-1">Claude/GPT 모델 선택, fallback, Top-K 벤치마킹 강도를 운영 UI에서 조절합니다.</p>
      </div>

      <div className="flex gap-2 border-b pb-2">
        <Link href="/settings/users" className="px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50">담당자 관리</Link>
        <Link href="/settings/secrets" className="px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50">시크릿 관리</Link>
        <Link href="/settings/ai-engine" className="px-3 py-2 rounded-lg text-sm bg-blue-50 text-blue-700 font-medium">AI 엔진 설정</Link>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700">
        ✅ 대표님 의도 기준: provider/model 선택, task별 라우팅, K값/가중치 변경을 여기서 바로 제어합니다.
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border p-6 text-sm text-gray-500">불러오는 중...</div>
      ) : (
        <>
          <div className="space-y-4">
            {Object.entries(groupedProviders).map(([providerName, rows]) => (
              <div key={providerName} className="bg-white rounded-xl border overflow-hidden">
                <div className="px-4 py-3 border-b bg-gray-50 font-semibold text-sm uppercase">{providerName}</div>
                <div className="divide-y">
                  {rows.map((item) => (
                    <div key={item.id || `${item.provider_name}-${item.model_name}`} className="p-4 grid grid-cols-1 md:grid-cols-6 gap-3 items-center">
                      <div className="md:col-span-2">
                        <div className="font-medium text-sm">{item.label}</div>
                        <div className="text-xs text-gray-500">{item.model_name}</div>
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
                      <input
                        value={item.timeout_seconds}
                        onChange={(e) => setProviders((prev) => prev.map((row) => row.id === item.id ? { ...row, timeout_seconds: Number(e.target.value) || 60 } : row))}
                        className="rounded-lg border px-3 py-2 text-sm"
                        aria-label="Timeout seconds"
                      />
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
            <div className="px-4 py-3 border-b bg-gray-50 font-semibold text-sm">Task별 라우팅 / K값 설정</div>
            <div className="divide-y">
              {policies.map((policy) => (
                <div key={policy.task_type} className="p-4 space-y-3">
                  <div className="font-medium text-sm">{policy.task_type}</div>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    <input value={policy.primary_provider} onChange={(e) => setPolicies((prev) => prev.map((row) => row.task_type === policy.task_type ? { ...row, primary_provider: e.target.value } : row))} className="rounded-lg border px-3 py-2 text-sm" aria-label="기본 Provider" />
                    <input value={policy.primary_model} onChange={(e) => setPolicies((prev) => prev.map((row) => row.task_type === policy.task_type ? { ...row, primary_model: e.target.value } : row))} className="rounded-lg border px-3 py-2 text-sm" aria-label="기본 Model" />
                    <input value={policy.top_k} onChange={(e) => setPolicies((prev) => prev.map((row) => row.task_type === policy.task_type ? { ...row, top_k: Number(e.target.value) || 10 } : row))} className="rounded-lg border px-3 py-2 text-sm" aria-label="Top-K" />
                    <input value={policy.benchmark_window_days} onChange={(e) => setPolicies((prev) => prev.map((row) => row.task_type === policy.task_type ? { ...row, benchmark_window_days: Number(e.target.value) || 30 } : row))} className="rounded-lg border px-3 py-2 text-sm" aria-label="Window days" />
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <input value={policy.views_weight} onChange={(e) => setPolicies((prev) => prev.map((row) => row.task_type === policy.task_type ? { ...row, views_weight: Number(e.target.value) || 0 } : row))} className="rounded-lg border px-3 py-2 text-sm" aria-label="Views weight" />
                    <input value={policy.engagement_weight} onChange={(e) => setPolicies((prev) => prev.map((row) => row.task_type === policy.task_type ? { ...row, engagement_weight: Number(e.target.value) || 0 } : row))} className="rounded-lg border px-3 py-2 text-sm" aria-label="Engagement weight" />
                    <input value={policy.recency_weight} onChange={(e) => setPolicies((prev) => prev.map((row) => row.task_type === policy.task_type ? { ...row, recency_weight: Number(e.target.value) || 0 } : row))} className="rounded-lg border px-3 py-2 text-sm" aria-label="Recency weight" />
                    <input value={policy.action_language_weight} onChange={(e) => setPolicies((prev) => prev.map((row) => row.task_type === policy.task_type ? { ...row, action_language_weight: Number(e.target.value) || 0 } : row))} className="rounded-lg border px-3 py-2 text-sm" aria-label="Action language weight" />
                  </div>
                  <div className="flex items-center justify-between">
                    <label className="text-sm text-gray-600 flex items-center gap-2">
                      <input type="checkbox" checked={policy.fallback_enabled} onChange={(e) => setPolicies((prev) => prev.map((row) => row.task_type === policy.task_type ? { ...row, fallback_enabled: e.target.checked } : row))} />
                      Fallback 사용
                    </label>
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
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
