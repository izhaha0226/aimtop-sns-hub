"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { adminSecretsService, type AdminSecretItem } from "@/services/admin-secrets"

const sourceBadge: Record<string, string> = {
  db: "bg-blue-100 text-blue-700",
  env: "bg-amber-100 text-amber-700",
  empty: "bg-gray-100 text-gray-500",
}

const sourceLabel: Record<string, string> = {
  db: "관리자",
  env: ".env",
  empty: "미설정",
}

export default function SecretsPage() {
  const { isAdmin, loading: authLoading } = useAuth()
  const router = useRouter()
  const [items, setItems] = useState<AdminSecretItem[]>([])
  const [loading, setLoading] = useState(false)
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [enabledMap, setEnabledMap] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (!authLoading && !isAdmin) router.push("/dashboard")
  }, [isAdmin, authLoading, router])

  async function load() {
    setLoading(true)
    try {
      const data = await adminSecretsService.list()
      setItems(data)
      setEnabledMap(Object.fromEntries(data.map((item) => [item.secret_key, item.is_active])))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isAdmin) load().catch(console.error)
  }, [isAdmin])

  const grouped = useMemo(() => {
    return items.reduce<Record<string, AdminSecretItem[]>>((acc, item) => {
      acc[item.category] = acc[item.category] || []
      acc[item.category].push(item)
      return acc
    }, {})
  }, [items])

  if (authLoading) return null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">시크릿 관리</h1>
          <p className="text-sm text-gray-500 mt-1">관리자 저장값이 우선이고, 없으면 기존 .env 값을 fallback으로 사용합니다.</p>
        </div>
        <button
          onClick={() => load().catch(console.error)}
          className="px-4 py-2 rounded-lg border text-sm hover:bg-gray-50"
        >
          새로고침
        </button>
      </div>

      <div className="flex gap-2 border-b pb-2">
        <Link href="/settings/users" className="px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50">담당자 관리</Link>
        <Link href="/settings/secrets" className="px-3 py-2 rounded-lg text-sm bg-blue-50 text-blue-700 font-medium">시크릿 관리</Link>
        <Link href="/settings/ai-engine" className="px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50">AI 엔진 설정</Link>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
        ✅ Fal.ai / OAuth / 알림용 키를 여기서 바꾸면 재배포 없이 바로 운영값으로 우선 사용합니다.
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border p-6 text-sm text-gray-500">불러오는 중...</div>
      ) : (
        Object.entries(grouped).map(([category, secrets]) => (
          <div key={category} className="bg-white rounded-xl border overflow-hidden">
            <div className="px-4 py-3 border-b bg-gray-50 font-semibold text-sm">{category}</div>
            <div className="divide-y">
              {secrets.map((item) => (
                <div key={item.secret_key} className="p-4 space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-medium text-sm">{item.label}</div>
                      <div className="text-xs text-gray-500 mt-1">{item.description}</div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`px-2 py-1 rounded-full text-xs ${sourceBadge[item.source] || sourceBadge.empty}`}>
                        {sourceLabel[item.source] || item.source}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs ${item.configured ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                        {item.configured ? "설정됨" : "비어있음"}
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-gray-500">현재값: {item.masked_value || "(없음)"}</div>

                  <textarea
                    value={drafts[item.secret_key] || ""}
                    onChange={(e) => setDrafts((prev) => ({ ...prev, [item.secret_key]: e.target.value }))}
                    rows={2}
                    placeholder="새 값을 입력하면 덮어씁니다. 비워두고 저장하면 기존 값 유지"
                    className="w-full rounded-lg border px-3 py-2 text-sm"
                  />

                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-sm text-gray-600">
                      <input
                        type="checkbox"
                        checked={enabledMap[item.secret_key] ?? item.is_active}
                        onChange={(e) => setEnabledMap((prev) => ({ ...prev, [item.secret_key]: e.target.checked }))}
                      />
                      활성화
                    </label>
                    <button
                      onClick={async () => {
                        try {
                          setSavingKey(item.secret_key)
                          const updated = await adminSecretsService.update(item.secret_key, {
                            value: drafts[item.secret_key] || undefined,
                            is_active: enabledMap[item.secret_key] ?? item.is_active,
                          })
                          setItems((prev) => prev.map((x) => (x.secret_key === item.secret_key ? updated : x)))
                          setDrafts((prev) => ({ ...prev, [item.secret_key]: "" }))
                        } catch (error) {
                          console.error(error)
                          alert("저장 실패")
                        } finally {
                          setSavingKey(null)
                        }
                      }}
                      disabled={savingKey === item.secret_key}
                      className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-50"
                    >
                      {savingKey === item.secret_key ? "저장 중..." : "저장"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
