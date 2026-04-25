"use client"
import { useEffect, useMemo, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { AlertCircle, ArrowLeft, CalendarClock, CheckCircle, ExternalLink, Link2, MailPlus, Send, Trash2, XCircle, Zap } from "lucide-react"
import { contentsService } from "@/services/contents"
import { approvalsService, type ExternalApprovalItem } from "@/services/approvals"
import { channelsService, getTokenHealth, isAutoPublishSupported, type ChannelConnection } from "@/services/channels"
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
  const [channels, setChannels] = useState<ChannelConnection[]>([])
  const [externalApprovals, setExternalApprovals] = useState<ExternalApprovalItem[]>([])
  const [selectedChannelId, setSelectedChannelId] = useState("")
  const [scheduleAt, setScheduleAt] = useState("")
  const [reviewerName, setReviewerName] = useState("")
  const [reviewerEmail, setReviewerEmail] = useState("")
  const [expiresHours, setExpiresHours] = useState("72")
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionNotice, setActionNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [memoModal, setMemoModal] = useState<"approve" | "reject" | "schedule" | "external-approval" | null>(null)
  const [memo, setMemo] = useState("")
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const item = await contentsService.get(id)
        setContent(item)
        const [channelItems, approvalItems] = await Promise.all([
          channelsService.list(item.client_id),
          approvalsService.listForContent(id).catch(() => []),
        ])
        setChannels(channelItems)
        setExternalApprovals(approvalItems)
        setSelectedChannelId(item.channel_connection_id || channelItems.find((channel) => channel.is_connected && getTokenHealth(channel.token_expires_at) !== "reauth_required")?.id || "")
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [id])

  const connectedChannels = useMemo(
    () => channels.filter((channel) => channel.is_connected),
    [channels]
  )
  const availableChannels = useMemo(
    () => connectedChannels.filter((channel) => getTokenHealth(channel.token_expires_at) !== "reauth_required" && isAutoPublishSupported(channel.channel_type)),
    [connectedChannels]
  )
  const selectedChannel = connectedChannels.find((channel) => channel.id === selectedChannelId)
  const selectedChannelHealth = getTokenHealth(selectedChannel?.token_expires_at)
  const selectedChannelAutoPublishSupported = isAutoPublishSupported(selectedChannel?.channel_type)
  const hasPublishEvidence = Boolean(content?.platform_post_id || content?.published_url)
  const hasAnyPublishTrace = Boolean(content?.platform_post_id || content?.published_url || content?.published_at)
  const publishedWithoutEvidence = content?.status === "published" && !hasPublishEvidence
  const failedWithStaleEvidence = content?.status === "failed" && hasAnyPublishTrace

  function getErrorMessage(error: unknown, fallback: string) {
    if (
      typeof error === "object" &&
      error !== null &&
      "response" in error &&
      typeof (error as { response?: unknown }).response === "object" &&
      (error as { response?: { data?: unknown } }).response?.data &&
      typeof (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === "string"
    ) {
      return (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || fallback
    }
    return fallback
  }

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
    setActionError(null)
    setActionNotice(null)
    setActionLoading(true)
    try {
      const updated = await contentsService.requestApproval(id)
      setContent(updated)
    } catch (err: unknown) {
      console.error(err)
      setActionError(getErrorMessage(err, "승인 요청에 실패했습니다"))
    } finally {
      setActionLoading(false)
    }
  }

  async function handleApproveOrReject() {
    if (!memoModal || memoModal === "schedule") return
    setActionError(null)
    setActionLoading(true)
    try {
      const updated =
        memoModal === "approve"
          ? await contentsService.approveContent(id, memo)
          : await contentsService.rejectContent(id, memo)
      setContent(updated)
      setMemoModal(null)
      setMemo("")
    } catch (err: unknown) {
      console.error(err)
      setActionError(getErrorMessage(err, "처리에 실패했습니다"))
    } finally {
      setActionLoading(false)
    }
  }

  async function handlePublishNow() {
    if (!selectedChannelId) {
      setActionError("발행할 채널을 선택해 주세요")
      return
    }
    if (selectedChannelHealth === "reauth_required") {
      setActionError("재인증이 필요한 채널은 발행할 수 없습니다")
      return
    }
    if (!selectedChannelAutoPublishSupported) {
      setActionError("선택한 채널은 아직 실제 발행 자동화를 지원하지 않습니다")
      return
    }
    if (!confirm("지금 바로 발행하시겠습니까?")) return
    setActionError(null)
    setActionLoading(true)
    try {
      const updated = await contentsService.publishNow(id, selectedChannelId)
      setContent(updated)
    } catch (err: unknown) {
      console.error(err)
      setActionError(getErrorMessage(err, "즉시 발행에 실패했습니다"))
    } finally {
      setActionLoading(false)
    }
  }

  async function handleSchedule() {
    if (!selectedChannelId) {
      setActionError("예약할 채널을 선택해 주세요")
      return
    }
    if (!scheduleAt) {
      setActionError("예약 시간을 선택해 주세요")
      return
    }
    if (selectedChannelHealth === "reauth_required") {
      setActionError("재인증이 필요한 채널은 예약할 수 없습니다")
      return
    }
    if (!selectedChannelAutoPublishSupported) {
      setActionError("선택한 채널은 아직 실제 발행 자동화를 지원하지 않습니다")
      return
    }

    setActionError(null)
    setActionLoading(true)
    try {
      await contentsService.schedule(id, new Date(scheduleAt).toISOString(), selectedChannelId)
      setContent((prev) => prev ? {
        ...prev,
        status: "scheduled",
        scheduled_at: new Date(scheduleAt).toISOString(),
        channel_connection_id: selectedChannelId,
      } : prev)
      setMemoModal(null)
    } catch (err: unknown) {
      console.error(err)
      setActionError(getErrorMessage(err, "예약 발행에 실패했습니다"))
    } finally {
      setActionLoading(false)
    }
  }

  async function handleCreateExternalApproval() {
    if (!reviewerName.trim() || !reviewerEmail.trim()) {
      setActionError("검토자 이름과 이메일을 입력해 주세요")
      return
    }
    setActionError(null)
    setActionNotice(null)
    setActionLoading(true)
    try {
      const created = await approvalsService.create(id, {
        reviewer_name: reviewerName.trim(),
        reviewer_email: reviewerEmail.trim(),
        expires_hours: Number(expiresHours) || 72,
      })
      const latest = await approvalsService.listForContent(id)
      setExternalApprovals(latest)
      setMemoModal(null)
      setReviewerName("")
      setReviewerEmail("")
      setExpiresHours("72")
      setActionNotice(created.email_sent === false ? "승인 요청은 생성됐지만 이메일 발송은 실패했습니다. 링크를 직접 전달해 주세요." : "외부 승인 요청을 발송했습니다.")
    } catch (err: unknown) {
      console.error(err)
      setActionError(getErrorMessage(err, "외부 승인 요청에 실패했습니다"))
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

        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-gray-700">발행 채널</p>
              <p className="text-xs text-gray-400 mt-1">재인증 필요 또는 미지원 채널은 자동 발행/예약에 사용할 수 없습니다</p>
            </div>
            <div className="text-xs text-gray-500">연결 채널 {connectedChannels.length}개</div>
          </div>

          <select
            value={selectedChannelId}
            onChange={(e) => {
              setSelectedChannelId(e.target.value)
              setActionError(null)
            }}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">발행 채널 선택</option>
            {connectedChannels.map((channel) => {
              const health = getTokenHealth(channel.token_expires_at)
              const unsupported = !isAutoPublishSupported(channel.channel_type)
              const disabled = health === "reauth_required" || unsupported
              return (
                <option key={channel.id} value={channel.id} disabled={disabled}>
                  {channel.channel_type}{channel.account_name ? ` · ${channel.account_name}` : ""}{disabled ? unsupported ? " (자동발행 미지원)" : " (재인증 필요)" : health === "expiring" ? " (만료 임박)" : ""}
                </option>
              )
            })}
          </select>

          {selectedChannel && (
            <div className={`rounded-lg px-3 py-2 text-xs ${!selectedChannelAutoPublishSupported ? "bg-gray-100 text-gray-700 border border-gray-200" : selectedChannelHealth === "expiring" ? "bg-yellow-50 text-yellow-700 border border-yellow-200" : "bg-blue-50 text-blue-700 border border-blue-200"}`}>
              {selectedChannel.channel_type}{selectedChannel.account_name ? ` · ${selectedChannel.account_name}` : ""}
              {!selectedChannelAutoPublishSupported ? " · 현재 연동만 지원, 자동 발행 미지원" : selectedChannel.token_expires_at ? ` · 만료 ${new Date(selectedChannel.token_expires_at).toLocaleString("ko-KR")}` : " · 만료시각 미확인"}
            </div>
          )}

          {availableChannels.length === 0 && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              자동 발행 가능한 채널이 없습니다. 지원 채널 연동 또는 재연동이 필요합니다.
            </div>
          )}
        </div>

        {content.memo && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-xs font-medium text-yellow-700 mb-0.5">메모</p>
            <p className="text-sm text-yellow-800">{content.memo}</p>
          </div>
        )}

        <div className={`rounded-lg border px-4 py-3 text-sm ${publishedWithoutEvidence ? "border-amber-200 bg-amber-50 text-amber-800" : failedWithStaleEvidence ? "border-rose-200 bg-rose-50 text-rose-800" : hasPublishEvidence ? "border-blue-200 bg-blue-50 text-blue-800" : "border-gray-200 bg-gray-50 text-gray-700"}`}>
          <div className="flex items-center gap-2 font-medium">
            <Link2 size={14} />
            {publishedWithoutEvidence
              ? "published 상태지만 외부 발행 증거는 아직 없습니다"
              : failedWithStaleEvidence
                ? "실패 상태인데 이전 발행 흔적이 남아 있습니다"
                : hasPublishEvidence
                  ? "외부 발행 증거가 기록되어 있습니다"
                  : "외부 발행 증거 없음"}
          </div>
          <div className="mt-2 space-y-1 text-xs">
            <div>내부 상태: {STATUS_LABELS[content.status]}</div>
            <div>platform_post_id: {content.platform_post_id || "-"}</div>
            <div className="break-all">published_url: {content.published_url || "-"}</div>
            <div>published_at: {content.published_at ? new Date(content.published_at).toLocaleString("ko-KR") : "-"}</div>
          </div>
          {content.published_url && (
            <a href={content.published_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 underline underline-offset-2">
              외부 링크 열기
              <ExternalLink size={12} />
            </a>
          )}
          {publishedWithoutEvidence && (
            <div className="mt-2 text-xs text-amber-700">status=published 만으로 실발행 성공으로 판단하지 않도록 주의가 필요합니다.</div>
          )}
          {failedWithStaleEvidence && (
            <div className="mt-2 text-xs text-rose-700">실패 처리 후에도 이전 증거 필드가 남아 있으면 운영자가 성공처럼 오해할 수 있습니다.</div>
          )}
        </div>

        {content.author_name && (
          <p className="text-xs text-gray-400">작성자: {content.author_name}</p>
        )}
      </div>

      {actionNotice && (
        <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 flex items-center gap-2">
          <CheckCircle size={16} />
          {actionNotice}
        </div>
      )}

      {actionError && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle size={16} />
          {actionError}
        </div>
      )}

      <div className="mt-4 rounded-xl border bg-white p-5 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-800">외부 승인</h2>
            <p className="text-xs text-gray-400 mt-1">클라이언트/외부 검토자에게 토큰 링크를 발송합니다.</p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setActionError(null)
              setActionNotice(null)
              setMemoModal("external-approval")
            }}
          >
            <MailPlus size={14} className="mr-1.5" />
            외부 승인 요청
          </Button>
        </div>

        {externalApprovals.length === 0 ? (
          <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-500">아직 발송된 외부 승인 요청이 없습니다.</div>
        ) : (
          <div className="space-y-2">
            {externalApprovals.map((item) => (
              <div key={item.id} className="rounded-lg border px-4 py-3 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-gray-800">{item.reviewer_name} · {item.reviewer_email}</p>
                  <p className="text-xs text-gray-400 mt-1">생성 {new Date(item.created_at).toLocaleString("ko-KR")}</p>
                  <p className="text-xs text-gray-500 mt-1">만료 {item.expires_at ? new Date(item.expires_at).toLocaleString("ko-KR") : "-"}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${item.status === "approved" ? "bg-green-50 text-green-700" : item.status === "rejected" ? "bg-red-50 text-red-700" : item.expired ? "bg-gray-100 text-gray-600" : "bg-blue-50 text-blue-700"}`}>
                    {item.status === "approved" ? "승인 완료" : item.status === "rejected" ? "수정 요청" : item.expired ? "만료됨" : "검토 대기"}
                  </span>
                  {item.review_link && (
                    <a href={item.review_link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline">
                      링크 열기
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
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
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setActionError(null)
                setActionNotice(null)
                setMemoModal("schedule")
              }}
              disabled={availableChannels.length === 0}
            >
              <CalendarClock size={14} className="mr-1.5" />
              예약 발행
            </Button>
            <Button
              size="sm"
              onClick={handlePublishNow}
              loading={actionLoading}
              disabled={availableChannels.length === 0 || !selectedChannelId || selectedChannelHealth === "reauth_required" || !selectedChannelAutoPublishSupported}
            >
              <Zap size={14} className="mr-1.5" />
              지금 발행
            </Button>
          </>
        )}

        {content.status === "published" && (
          <span className={`text-sm py-1 ${publishedWithoutEvidence ? "text-amber-700" : "text-gray-400"}`}>
            {publishedWithoutEvidence
              ? "published 상태지만 증거 미확인"
              : content.published_at
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
          setReviewerName("")
          setReviewerEmail("")
          setExpiresHours("72")
        }}
        title={memoModal === "approve" ? "콘텐츠 승인" : memoModal === "reject" ? "콘텐츠 반려" : memoModal === "schedule" ? "예약 발행" : "외부 승인 요청"}
      >
        {memoModal === "external-approval" ? (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">검토자에게 이메일로 승인 링크를 발송합니다.</p>
            <input
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              placeholder="검토자 이름"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              value={reviewerEmail}
              onChange={(e) => setReviewerEmail(e.target.value)}
              placeholder="reviewer@example.com"
              type="email"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={expiresHours}
              onChange={(e) => setExpiresHours(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="24">24시간</option>
              <option value="72">72시간</option>
              <option value="168">7일</option>
            </select>
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" size="sm" onClick={() => setMemoModal(null)}>
                취소
              </Button>
              <Button size="sm" onClick={handleCreateExternalApproval} loading={actionLoading}>
                발송
              </Button>
            </div>
          </div>
        ) : memoModal === "schedule" ? (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">예약 시간을 선택하면 자동 발행 지원 채널에 한해 발행 대기 상태가 됩니다.</p>
            <input
              type="datetime-local"
              value={scheduleAt}
              onChange={(e) => setScheduleAt(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" size="sm" onClick={() => setMemoModal(null)}>
                취소
              </Button>
              <Button size="sm" onClick={handleSchedule} loading={actionLoading} disabled={!selectedChannelAutoPublishSupported}>
                예약 저장
              </Button>
            </div>
          </div>
        ) : (
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
        )}
      </Modal>
    </div>
  )
}
