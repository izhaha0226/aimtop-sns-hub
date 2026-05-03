"use client"
import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { FileText, Loader2, Plus, Trash2 } from "lucide-react"
import { contentsService } from "@/services/contents"
import { useSelectedClient } from "@/hooks/useSelectedClient"
import type { Content } from "@/types/content"
import { STATUS_LABELS, STATUS_COLORS, POST_TYPE_LABELS, POST_TYPE_COLORS } from "@/types/content"

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "전체" },
  { value: "draft", label: "임시저장" },
  { value: "pending_approval", label: "승인 대기" },
  { value: "approved", label: "승인됨" },
  { value: "published", label: "발행됨" },
]

type WeekGroup = {
  key: string
  label: string
  items: Content[]
}

function weekNumberOf(content: Content) {
  const rawWeek = content.source_metadata?.week
  const parsed = typeof rawWeek === "number" ? rawWeek : Number(rawWeek)
  if (Number.isFinite(parsed) && parsed > 0) return parsed

  const titleMatch = content.title.match(/(\d+)주차/)
  if (titleMatch) return Number(titleMatch[1])

  return 999
}

function sequenceOf(content: Content, fallback: number) {
  const rawSequence = content.source_metadata?.sequence
  const parsed = typeof rawSequence === "number" ? rawSequence : Number(rawSequence)
  if (Number.isFinite(parsed) && parsed > 0) return parsed

  const hashMatch = content.title.match(/#(\d+)$/)
  if (hashMatch) return Number(hashMatch[1])

  const trailingMatch = content.title.match(/(?:·|\s)(\d{1,3})$/)
  if (trailingMatch) return Number(trailingMatch[1])

  return fallback + 1
}

function cleanDisplayTitle(content: Content, fallbackIndex: number) {
  const metadataTitle = content.source_metadata?.display_title
  const baseTitle = typeof metadataTitle === "string" && metadataTitle.trim() ? metadataTitle : content.title
  const withoutBrandPrefix = baseTitle.replace(/^\[[^\]]+\]\s*/, "")
  const withoutHashSequence = withoutBrandPrefix.replace(/\s+#\d+$/, "")
  const channel = content.source_metadata?.channel
  const format = content.source_metadata?.format
  const week = weekNumberOf(content)
  const sequence = sequenceOf(content, fallbackIndex)

  if (typeof metadataTitle === "string" && metadataTitle.trim()) return metadataTitle.trim()
  if (week !== 999 && channel && format) return `${week}주차 · ${channel} · ${format}`
  return withoutHashSequence.trim() || `콘텐츠 ${String(sequence).padStart(2, "0")}`
}

function groupContentsByWeek(contents: Content[]): WeekGroup[] {
  const sorted = [...contents].sort((a, b) => {
    const weekDiff = weekNumberOf(a) - weekNumberOf(b)
    if (weekDiff !== 0) return weekDiff
    const seqDiff = sequenceOf(a, 0) - sequenceOf(b, 0)
    if (seqDiff !== 0) return seqDiff
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  })

  const groups = new Map<string, Content[]>()
  for (const item of sorted) {
    const week = weekNumberOf(item)
    const key = week === 999 ? "etc" : String(week)
    groups.set(key, [...(groups.get(key) || []), item])
  }

  return Array.from(groups.entries()).map(([key, items]) => ({
    key,
    label: key === "etc" ? "미분류 콘텐츠" : `${key}주차 콘텐츠`,
    items,
  }))
}

export default function ContentsPage() {
  const router = useRouter()
  const { selectedClientId, selectedClient, loading: clientLoading } = useSelectedClient()
  const [contents, setContents] = useState<Content[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState("")
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (clientLoading) return
    let cancelled = false
    const fetchContents = async () => {
      setLoading(true)
      setError(null)
      try {
        if (!selectedClientId) {
          setContents([])
          return
        }
        const data = await contentsService.list({
          client_id: selectedClientId,
          ...(statusFilter ? { status: statusFilter } : {}),
        })
        if (!cancelled) setContents(data)
      } catch (err) {
        console.error(err)
        if (!cancelled) setError("콘텐츠 목록을 불러오지 못했습니다")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchContents()
    return () => { cancelled = true }
  }, [clientLoading, selectedClientId, statusFilter])

  const weekGroups = useMemo(() => groupContentsByWeek(contents), [contents])

  const deleteContent = async (content: Content) => {
    const title = cleanDisplayTitle(content, 0)
    if (!window.confirm(`이 콘텐츠를 삭제할까요?\n${title}`)) return

    setDeletingId(content.id)
    setNotice(null)
    setError(null)
    try {
      await contentsService.delete(content.id)
      setContents((items) => items.filter((item) => item.id !== content.id))
      setNotice("콘텐츠를 삭제했습니다")
    } catch (err) {
      console.error(err)
      setError("콘텐츠 삭제에 실패했습니다")
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold">콘텐츠</h1>
          <p className="text-sm text-gray-500 mt-1">현재 클라이언트({clientLoading ? "확인 중..." : selectedClient?.name || "미선택"})의 콘텐츠만 표시합니다.</p>
        </div>
        <button
          onClick={() => router.push("/contents/new")}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} />
          새 콘텐츠
        </button>
      </div>

      <div className="flex gap-1 mb-4 bg-white border rounded-lg p-1 w-fit">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
              statusFilter === f.value
                ? "bg-blue-600 text-white font-medium"
                : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {(notice || error) && (
        <div className={`mb-4 rounded-lg border px-4 py-3 text-sm ${error ? "border-red-200 bg-red-50 text-red-700" : "border-blue-200 bg-blue-50 text-blue-700"}`}>
          {error || notice}
        </div>
      )}

      {loading || clientLoading ? (
        <div className="text-center py-12 text-gray-400">불러오는 중...</div>
      ) : !selectedClientId ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <FileText size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400 text-sm">상단에서 클라이언트를 선택해주세요</p>
        </div>
      ) : contents.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <FileText size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400 text-sm">콘텐츠가 없습니다</p>
        </div>
      ) : (
        <div className="space-y-4">
          {weekGroups.map((group) => (
            <section key={group.key} className="bg-white rounded-xl border overflow-hidden">
              <div className="flex items-center justify-between border-b bg-gray-50 px-4 py-3">
                <div>
                  <h2 className="text-sm font-semibold text-gray-900">{group.label}</h2>
                  <p className="text-xs text-gray-500 mt-0.5">{group.items.length}개 콘텐츠 · 제목에서 중복 브랜드 prefix 제거</p>
                </div>
                <span className="rounded-full bg-white border px-2.5 py-1 text-xs font-medium text-gray-600">
                  {group.items.length} items
                </span>
              </div>

              <div className="divide-y divide-gray-100">
                {group.items.map((c, index) => {
                  const sequence = sequenceOf(c, index)
                  const displayTitle = cleanDisplayTitle(c, index)
                  const channel = c.source_metadata?.channel
                  const objective = c.source_metadata?.objective
                  const deleting = deletingId === c.id

                  return (
                    <div
                      key={c.id}
                      onClick={() => router.push(`/contents/${c.id}`)}
                      className="grid grid-cols-[56px_1fr_110px_100px_96px_96px] items-center gap-3 px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-900 text-xs font-bold text-white">
                        {String(sequence).padStart(2, "0")}
                      </div>

                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-900 truncate">{displayTitle}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                          {channel && <span className="rounded bg-gray-100 px-1.5 py-0.5">{channel}</span>}
                          {objective && <span className="truncate max-w-sm">목표: {objective}</span>}
                          {c.client_name && <span>{c.client_name}</span>}
                        </div>
                      </div>

                      <div>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${POST_TYPE_COLORS[c.post_type]}`}>
                          {POST_TYPE_LABELS[c.post_type]}
                        </span>
                      </div>

                      <div>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[c.status]}`}>
                          {STATUS_LABELS[c.status]}
                        </span>
                      </div>

                      <div className="text-sm text-gray-400">
                        {new Date(c.created_at).toLocaleDateString("ko-KR")}
                      </div>

                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          deleteContent(c)
                        }}
                        disabled={deleting}
                        className="inline-flex items-center justify-center gap-1 rounded-lg border border-red-100 px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                        삭제
                      </button>
                    </div>
                  )
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
