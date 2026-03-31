"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Plus, FileText } from "lucide-react"
import { contentsService } from "@/services/contents"
import type { Content } from "@/types/content"
import { STATUS_LABELS, STATUS_COLORS, POST_TYPE_LABELS, POST_TYPE_COLORS } from "@/types/content"

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "전체" },
  { value: "draft", label: "임시저장" },
  { value: "pending_approval", label: "승인 대기" },
  { value: "approved", label: "승인됨" },
  { value: "published", label: "발행됨" },
]

export default function ContentsPage() {
  const router = useRouter()
  const [contents, setContents] = useState<Content[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState("")

  useEffect(() => {
    let cancelled = false
    const fetchContents = async () => {
      try {
        const data = await contentsService.list(statusFilter ? { status: statusFilter } : undefined)
        if (!cancelled) setContents(data)
      } catch (err) {
        console.error(err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchContents()
    return () => { cancelled = true }
  }, [statusFilter])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">콘텐츠</h1>
        <button
          onClick={() => router.push("/contents/new")}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} />
          새 콘텐츠
        </button>
      </div>

      {/* Status filter tabs */}
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

      {loading ? (
        <div className="text-center py-12 text-gray-400">불러오는 중...</div>
      ) : contents.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <FileText size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400 text-sm">콘텐츠가 없습니다</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500">
                <th className="text-left px-4 py-3 font-medium">제목</th>
                <th className="text-left px-4 py-3 font-medium">유형</th>
                <th className="text-left px-4 py-3 font-medium">상태</th>
                <th className="text-left px-4 py-3 font-medium">작성자</th>
                <th className="text-left px-4 py-3 font-medium">날짜</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {contents.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => router.push(`/contents/${c.id}`)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900 truncate max-w-xs">{c.title}</p>
                    {c.client_name && (
                      <p className="text-xs text-gray-400 mt-0.5">{c.client_name}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        POST_TYPE_COLORS[c.post_type]
                      }`}
                    >
                      {POST_TYPE_LABELS[c.post_type]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        STATUS_COLORS[c.status]
                      }`}
                    >
                      {STATUS_LABELS[c.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {c.author_name || "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400">
                    {new Date(c.created_at).toLocaleDateString("ko-KR")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
