"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { AlertCircle, CheckCircle2, Clock3, Mail, XCircle } from "lucide-react"
import { approvalsService, type ExternalApprovalDetail } from "@/services/approvals"
import { Button } from "@/components/common/Button"

export default function ExternalApprovalPage() {
  const params = useParams<{ token: string }>()
  const token = params.token

  const [approval, setApproval] = useState<ExternalApprovalDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState<"approved" | "rejected" | null>(null)
  const [feedback, setFeedback] = useState("")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const data = await approvalsService.getByToken(token)
        setApproval(data)
      } catch (err: unknown) {
        const detail =
          typeof err === "object" &&
          err !== null &&
          "response" in err &&
          typeof (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === "string"
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : "승인 요청을 불러오지 못했습니다"
        setError(detail || "승인 요청을 불러오지 못했습니다")
      } finally {
        setLoading(false)
      }
    }
    if (token) void load()
  }, [token])

  async function handleRespond(status: "approved" | "rejected") {
    if (!approval || approval.expired || approval.status !== "pending") return
    setSubmitting(status)
    setError(null)
    try {
      const updated = await approvalsService.respond(token, status, feedback)
      setApproval((prev) => prev ? { ...prev, ...updated } : prev)
    } catch (err: unknown) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === "string"
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : "응답 처리에 실패했습니다"
      setError(detail || "응답 처리에 실패했습니다")
    } finally {
      setSubmitting(null)
    }
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">불러오는 중...</div>
  }

  if (error && !approval) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="w-full max-w-xl rounded-2xl border bg-white p-8 text-center">
          <AlertCircle className="mx-auto mb-3 text-red-500" size={28} />
          <h1 className="text-xl font-bold">외부 승인 요청을 찾을 수 없습니다</h1>
          <p className="mt-2 text-sm text-gray-500">{error}</p>
        </div>
      </div>
    )
  }

  const statusMeta = approval?.status === "approved"
    ? { label: "승인 완료", className: "bg-green-50 text-green-700 border-green-200", icon: <CheckCircle2 size={16} /> }
    : approval?.status === "rejected"
      ? { label: "수정 요청", className: "bg-red-50 text-red-700 border-red-200", icon: <XCircle size={16} /> }
      : approval?.expired
        ? { label: "만료됨", className: "bg-gray-100 text-gray-600 border-gray-200", icon: <Clock3 size={16} /> }
        : { label: "검토 대기", className: "bg-blue-50 text-blue-700 border-blue-200", icon: <Mail size={16} /> }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="mx-auto max-w-3xl rounded-2xl border bg-white shadow-sm overflow-hidden">
        <div className="border-b bg-gradient-to-r from-blue-50 to-white px-6 py-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-blue-600">AimTop SNS Hub</p>
              <h1 className="mt-1 text-2xl font-bold text-gray-900">외부 승인 요청</h1>
            </div>
            <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium ${statusMeta.className}`}>
              {statusMeta.icon}
              {statusMeta.label}
            </span>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <section className="space-y-2">
            <p className="text-sm text-gray-500">검토자</p>
            <div className="rounded-xl border px-4 py-3">
              <p className="font-semibold text-gray-900">{approval?.reviewer_name}</p>
              <p className="text-sm text-gray-500">{approval?.reviewer_email}</p>
            </div>
          </section>

          <section className="space-y-2">
            <p className="text-sm text-gray-500">콘텐츠 정보</p>
            <div className="rounded-xl border px-4 py-4 space-y-3">
              <div>
                <p className="text-xs text-gray-400">제목</p>
                <p className="text-lg font-semibold text-gray-900">{approval?.content?.title || "제목 없음"}</p>
              </div>
              {approval?.content?.post_type && (
                <div>
                  <p className="text-xs text-gray-400">유형</p>
                  <p className="text-sm text-gray-700">{approval.content.post_type}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-gray-400">본문</p>
                <p className="whitespace-pre-wrap text-sm leading-6 text-gray-700">{approval?.content?.text || "본문이 없습니다."}</p>
              </div>
              {!!approval?.content?.media_urls?.length && (
                <div>
                  <p className="text-xs text-gray-400 mb-2">첨부 이미지</p>
                  <div className="flex flex-wrap gap-2">
                    {approval.content.media_urls.map((url) => (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img key={url} src={url} alt="" className="h-24 w-24 rounded-lg border object-cover" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border px-4 py-3">
              <p className="text-xs text-gray-400">요청일</p>
              <p className="mt-1 text-sm text-gray-700">{approval?.created_at ? new Date(approval.created_at).toLocaleString("ko-KR") : "-"}</p>
            </div>
            <div className="rounded-xl border px-4 py-3">
              <p className="text-xs text-gray-400">만료일</p>
              <p className="mt-1 text-sm text-gray-700">{approval?.expires_at ? new Date(approval.expires_at).toLocaleString("ko-KR") : "-"}</p>
            </div>
          </section>

          {approval?.status === "pending" && !approval.expired ? (
            <section className="space-y-3">
              <p className="text-sm text-gray-500">검토 의견</p>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={5}
                placeholder="수정 요청이나 참고 메모가 있으면 남겨주세요."
                className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
              <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <Button variant="danger" onClick={() => void handleRespond("rejected")} loading={submitting === "rejected"}>
                  수정 요청
                </Button>
                <Button onClick={() => void handleRespond("approved")} loading={submitting === "approved"}>
                  승인
                </Button>
              </div>
            </section>
          ) : (
            <section className="rounded-xl border px-4 py-4 bg-gray-50">
              <p className="text-sm font-medium text-gray-700">최종 의견</p>
              <p className="mt-2 whitespace-pre-wrap text-sm text-gray-600">{approval?.feedback || "남겨진 의견이 없습니다."}</p>
              {approval?.responded_at && (
                <p className="mt-3 text-xs text-gray-400">응답 시각: {new Date(approval.responded_at).toLocaleString("ko-KR")}</p>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
