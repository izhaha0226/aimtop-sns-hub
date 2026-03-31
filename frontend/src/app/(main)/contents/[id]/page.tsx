"use client"
import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { ArrowLeft, Trash2, Send, CheckCircle, XCircle, Zap } from "lucide-react"
import { contentsService } from "@/services/contents"
import type { Content } from "@/types/content"
import { STATUS_LABELS, STATUS_COLORS, POST_TYPE_LABELS, POST_TYPE_COLORS } from "@/types/content"
import { Button } from "@/components/common/Button"
import { Modal } from "@/components/common/Modal"
import { useAuth } from "@/hooks/useAuth"

export default function ContentDetailPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const { isApprover } = useAuth()

  const [content, setContent] = useState<Content | null>(null)
  const [loading, setLoading] = useState(true)

  const [memoModal, setMemoModal] = useState<"approve" | "reject" | null>(null)
  const [memo, setMemo] = useState("")
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    contentsService
      .get(id)
      .then(setContent)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  async function handleDelete() {
    if (!confirm("콘텐츠를 삭제하시겠습니까?")) return
    try {
      await contentsService.delete(id)
      router.push("/contents")
    } catch (err) {
      console.error(err)
    }
  }

  async function handleRequestApproval() {
    setActionLoading(true)
    try {
      const updated = await contentsService.requestApproval(id)
      setContent(updated)
    } catch (err) {
      console.error(err)
    } finally {
      setActionLoading(false)
    }
  }

  async function handleApproveOrReject() {
    if (!memoModal) return
    setActionLoading(true)
    try {
      const updated =
        memoModal === "approve"
          ? await contentsService.approveContent(id, memo)
          : await contentsService.rejectContent(id, memo)
      setContent(updated)
      setMemoModal(null)
      setMemo("")
    } catch (err) {
      console.error(err)
    } finally {
      setActionLoading(false)
    }
  }

  async function handlePublishNow() {
    if (!confirm("지금 바로 발행하시겠습니까?")) return
    setActionLoading(true)
    try {
      const updated = await contentsService.publishNow(id)
      setContent(updated)
    } catch (err) {
      console.error(err)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-400">불러오는 중...</div>
  }

  if (!content) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">콘텐츠를 찾을 수 없습니다</p>
        <button onClick={() => router.push("/contents")} className="mt-3 text-blue-600 text-sm">
          목록으로 돌아가기
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.push("/contents")}
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"
        >
          <ArrowLeft size={18} />
        </button>
        <h1 className="text-xl font-bold flex-1 truncate">{content.title}</h1>
        <span
          className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
            STATUS_COLORS[content.status]
          }`}
        >
          {STATUS_LABELS[content.status]}
        </span>
      </div>

      {/* Content */}
      <div className="bg-white rounded-xl border p-6 space-y-5">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
              POST_TYPE_COLORS[content.post_type]
            }`}
          >
            {POST_TYPE_LABELS[content.post_type]}
          </span>
          {content.client_name && (
            <span className="text-sm text-gray-500">{content.client_name}</span>
          )}
          <span className="ml-auto text-xs text-gray-400">
            {new Date(content.created_at).toLocaleDateString("ko-KR", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </span>
        </div>

        {content.text && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-1.5">본문</p>
            <p className="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">
              {content.text}
            </p>
          </div>
        )}

        {content.hashtags.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-1.5">해시태그</p>
            <div className="flex flex-wrap gap-1.5">
              {content.hashtags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {content.media_urls.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-1.5">미디어</p>
            <div className="flex flex-wrap gap-2">
              {content.media_urls.map((url) => (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  key={url}
                  src={url}
                  alt=""
                  className="w-24 h-24 object-cover rounded-lg border"
                />
              ))}
            </div>
          </div>
        )}

        {content.memo && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-xs font-medium text-yellow-700 mb-0.5">메모</p>
            <p className="text-sm text-yellow-800">{content.memo}</p>
          </div>
        )}

        {content.author_name && (
          <p className="text-xs text-gray-400">작성자: {content.author_name}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-4 justify-end">
        {content.status === "draft" && (
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => router.push(`/contents/${id}/edit`)}
            >
              편집
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleRequestApproval}
              loading={actionLoading}
            >
              <Send size={14} className="mr-1.5" />
              승인 요청
            </Button>
            <Button variant="danger" size="sm" onClick={handleDelete}>
              <Trash2 size={14} className="mr-1.5" />
              삭제
            </Button>
          </>
        )}

        {content.status === "pending_approval" && isApprover && (
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setMemoModal("reject")}
            >
              <XCircle size={14} className="mr-1.5" />
              반려
            </Button>
            <Button size="sm" onClick={() => setMemoModal("approve")}>
              <CheckCircle size={14} className="mr-1.5" />
              승인
            </Button>
          </>
        )}

        {content.status === "approved" && (
          <Button size="sm" onClick={handlePublishNow} loading={actionLoading}>
            <Zap size={14} className="mr-1.5" />
            지금 발행
          </Button>
        )}

        {content.status === "published" && (
          <span className="text-sm text-gray-400 py-1">
            {content.published_at
              ? `${new Date(content.published_at).toLocaleString("ko-KR")} 발행됨`
              : "발행됨"}
          </span>
        )}
      </div>

      {/* Approve/Reject modal */}
      <Modal
        open={memoModal !== null}
        onClose={() => {
          setMemoModal(null)
          setMemo("")
        }}
        title={memoModal === "approve" ? "콘텐츠 승인" : "콘텐츠 반려"}
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            {memoModal === "approve"
              ? "이 콘텐츠를 승인하시겠습니까?"
              : "반려 사유를 입력해주세요."}
          </p>
          <textarea
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            placeholder="메모 (선택사항)"
            rows={3}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <div className="flex gap-2 justify-end">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setMemoModal(null)
                setMemo("")
              }}
            >
              취소
            </Button>
            <Button
              variant={memoModal === "reject" ? "danger" : "primary"}
              size="sm"
              onClick={handleApproveOrReject}
              loading={actionLoading}
            >
              {memoModal === "approve" ? "승인" : "반려"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
