"use client"
import { useEffect, useState, useCallback, useRef } from "react"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import { clientsService } from "@/services/clients"
import { channelsService, getTokenHealth, isAutoPublishSupported, type ChannelConnection } from "@/services/channels"
import { oauthService } from "@/services/oauth"
import { ArrowLeft, Pencil, Trash2, X, Link2, CheckCircle2, PlugZap, Unplug, AlertCircle } from "lucide-react"

const INDUSTRY_CATEGORIES = [
  "식품/음료", "리테일/유통", "교육/학원", "부동산/건설",
  "금융/보험", "뷰티/패션", "IT/테크", "건강/의료",
  "여행/레저", "자동차", "콘텐츠/미디어", "공공/비영리",
  "제조업", "전문서비스", "기타",
]

const CHANNEL_CARDS = [
  { id: "instagram", label: "인스타그램", desc: "피드/릴스/댓글", enabled: true },
  { id: "facebook", label: "페이스북", desc: "페이지 연동", enabled: true },
  { id: "threads", label: "Threads", desc: "Meta 계열 연동", enabled: true },
  { id: "youtube", label: "유튜브", desc: "영상/쇼츠/댓글", enabled: true },
  { id: "x", label: "X", desc: "트윗/답글", enabled: true },
  { id: "blog", label: "네이버 블로그", desc: "포스팅 발행", enabled: true },
  { id: "kakao", label: "카카오채널", desc: "프로필/메시지 권한", enabled: true },
  { id: "tiktok", label: "틱톡", desc: "프로필/영상 발행", enabled: true },
  { id: "linkedin", label: "LinkedIn", desc: "프로필/기업 페이지 연동", enabled: true },
]

interface Client {
  id: string
  name: string
  industry_category: string
  account_type: string
  brand_color: string | null
  logo: string | null
  created_at: string
}

interface FormData {
  name: string
  industry_category: string
  brand_color: string
  logo: string
  account_type: string
}

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [client, setClient] = useState<Client | null>(null)
  const [channels, setChannels] = useState<ChannelConnection[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [authLoading, setAuthLoading] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null)
  const [highlightedChannelId, setHighlightedChannelId] = useState<string | null>(null)
  const channelRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const [form, setForm] = useState<FormData>({ name: "", industry_category: "", brand_color: "#3B82F6", logo: "", account_type: "brand" })

  const load = useCallback(async () => {
    try {
      const [clientData, channelData] = await Promise.all([
        clientsService.get(id),
        channelsService.list(id),
      ])
      setClient(clientData)
      setChannels(channelData)
    } catch {
      router.push("/clients")
    } finally {
      setLoading(false)
    }
  }, [id, router])

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    const oauth = searchParams.get("oauth")
    const platform = searchParams.get("platform")
    const message = searchParams.get("message")
    if (!oauth || !platform) return

    if (oauth === "success") {
      setNotice({ type: "success", text: `${platform} 연동이 완료되었습니다.` })
      void load()
    } else {
      setNotice({ type: "error", text: `${platform} 연동 실패${message ? `: ${message}` : ""}` })
    }

    router.replace(`/clients/${id}`)
  }, [searchParams, router, id, load])

  useEffect(() => {
    const channelId = searchParams.get("channel")
    if (!channelId || channels.length === 0) return

    const timer = window.setTimeout(() => {
      channelRefs.current[channelId]?.scrollIntoView({ behavior: "smooth", block: "center" })
      setHighlightedChannelId(channelId)
    }, 150)

    const clearTimer = window.setTimeout(() => {
      setHighlightedChannelId((prev) => (prev === channelId ? null : prev))
    }, 3000)

    return () => {
      window.clearTimeout(timer)
      window.clearTimeout(clearTimer)
    }
  }, [searchParams, channels])

  const openEdit = () => {
    if (!client) return
    setForm({
      name: client.name,
      industry_category: client.industry_category,
      brand_color: client.brand_color || "#3B82F6",
      logo: client.logo || "",
      account_type: client.account_type,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.industry_category) return
    setSubmitting(true)
    try {
      await clientsService.update(id, {
        name: form.name.trim(),
        industry_category: form.industry_category,
        brand_color: form.brand_color || null,
        logo: form.logo.trim() || null,
        account_type: form.account_type,
      })
      setModalOpen(false)
      await load()
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!client) return
    if (!confirm(`"${client.name}" 클라이언트를 삭제하시겠습니까?\n삭제 후 복구할 수 없습니다.`)) return
    await clientsService.delete(id)
    router.push("/clients")
  }

  const handleConnect = async (platform: string) => {
    setAuthLoading(platform)
    setNotice(null)
    try {
      const origin = window.location.origin
      const redirectUri = `${origin}/api/v1/oauth/${platform}/callback`
      const frontendRedirect = `${origin}/clients/${id}`
      const authUrl = await oauthService.getAuthUrl(platform, id, redirectUri, frontendRedirect)
      window.location.href = authUrl
    } catch (error) {
      const message = error instanceof Error ? error.message : `${platform} 인증 URL 생성에 실패했습니다.`
      setNotice({ type: "error", text: message })
      setAuthLoading(null)
    }
  }

  const handleDisconnect = async (platform: string) => {
    if (!confirm(`${platform} 연동을 해제하시겠습니까?`)) return
    setAuthLoading(platform)
    setNotice(null)
    try {
      await oauthService.disconnect(platform, id)
      setNotice({ type: "success", text: `${platform} 연동을 해제했습니다.` })
      await load()
    } catch {
      setNotice({ type: "error", text: `${platform} 연동 해제에 실패했습니다.` })
    } finally {
      setAuthLoading(null)
    }
  }

  const channelMap = channels.reduce<Map<string, ChannelConnection>>((map, channel) => {
    if (!map.has(channel.channel_type)) map.set(channel.channel_type, channel)
    return map
  }, new Map())

  const connectedMap = channels.reduce<Map<string, ChannelConnection>>((map, channel) => {
    if (channel.is_connected && !map.has(channel.channel_type)) map.set(channel.channel_type, channel)
    return map
  }, new Map())

  const reauthChannels = Array.from(connectedMap.values()).filter(
    (channel) => getTokenHealth(channel.token_expires_at) === "reauth_required"
  )

  const tokenMeta = (tokenExpiresAt?: string | null) => {
    const health = getTokenHealth(tokenExpiresAt)
    if (health === "healthy") return { label: "토큰 정상", className: "bg-blue-50 text-blue-700 border border-blue-200" }
    if (health === "expiring") return { label: "만료 임박", className: "bg-yellow-50 text-yellow-700 border border-yellow-200" }
    if (health === "reauth_required") return { label: "재인증 필요", className: "bg-red-50 text-red-700 border border-red-200" }
    return { label: "만료일 미확인", className: "bg-gray-100 text-gray-600 border border-gray-200" }
  }

  if (loading) return <div className="text-center py-12 text-gray-400">불러오는 중...</div>
  if (!client) return null

  return (
    <div>
      <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6">
        <ArrowLeft size={16} />뒤로
      </button>

      <div className="bg-white rounded-xl border p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center text-white text-xl font-bold" style={{ backgroundColor: client.brand_color || "#3B82F6" }}>
              {client.name[0]}
            </div>
            <div>
              <h1 className="text-xl font-bold">{client.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="inline-block px-2.5 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full font-medium">{client.industry_category}</span>
                <span className="text-sm text-gray-400">{client.account_type}</span>
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button onClick={() => router.push(`/clients/${id}/benchmark`)} className="flex items-center gap-2 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors">
              <Link2 size={14} />벤치마킹
            </button>
            <button onClick={openEdit} className="flex items-center gap-2 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors">
              <Pencil size={14} />수정
            </button>
            <button onClick={handleDelete} className="flex items-center gap-2 px-3 py-2 border border-red-200 rounded-lg text-sm text-red-600 hover:bg-red-50 transition-colors">
              <Trash2 size={14} />삭제
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t">
          <div>
            <p className="text-xs text-gray-400 mb-1">브랜드 컬러</p>
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded" style={{ backgroundColor: client.brand_color || "#3B82F6" }} />
              <span className="text-sm">{client.brand_color || "#3B82F6"}</span>
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">계정 유형</p>
            <p className="text-sm">{client.account_type}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">등록일</p>
            <p className="text-sm">{new Date(client.created_at).toLocaleDateString("ko-KR")}</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-bold">채널별 인증 / 연동</h2>
            <p className="text-sm text-gray-500 mt-1">OAuth 연동과 실제 자동 발행 지원 범위를 분리해서 표시합니다.</p>
          </div>
        </div>

        {notice && (
          <div className={`mb-4 flex items-center gap-2 rounded-lg px-4 py-3 text-sm ${notice.type === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"}`}>
            {notice.type === "success" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            {notice.text}
          </div>
        )}

        {reauthChannels.length > 0 && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <p className="font-medium">재인증이 필요한 채널이 있습니다.</p>
            <p className="mt-1">{reauthChannels.map((channel) => channel.channel_type).join(", ")} 채널은 토큰이 만료되어 발행이 차단될 수 있습니다.</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          {CHANNEL_CARDS.map((channel) => {
            const channelState = channelMap.get(channel.id)
            const connected = connectedMap.get(channel.id)
            const tokenStatus = tokenMeta(connected?.token_expires_at)
            const hasSavedChannel = Boolean(channelState)
            const disconnectedReason = hasSavedChannel && !connected ? "토큰 없음 또는 OAuth 미완료" : null
            return (
              <div
                key={channel.id}
                ref={(el) => {
                  channelRefs.current[channel.id] = el
                }}
                className={`rounded-xl border p-4 transition-all ${highlightedChannelId === channel.id ? "ring-2 ring-blue-400 shadow-lg" : ""} ${channel.enabled ? "bg-white" : "bg-gray-50"}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold">{channel.label}</h3>
                      {connected ? (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200">연동됨</span>
                      ) : hasSavedChannel ? (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-orange-50 text-orange-700 border border-orange-200">토큰 없음</span>
                      ) : channel.enabled ? (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">미연동</span>
                      ) : (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">미구현</span>
                      )}
                      <span className={`text-[11px] px-2 py-0.5 rounded-full ${isAutoPublishSupported(channel.id) ? "bg-blue-50 text-blue-700 border border-blue-200" : "bg-gray-100 text-gray-600 border border-gray-200"}`}>
                        {isAutoPublishSupported(channel.id) ? "자동발행 지원" : "연동만 지원"}
                      </span>
                      {connected && (
                        <span className={`text-[11px] px-2 py-0.5 rounded-full ${tokenStatus.className}`}>{tokenStatus.label}</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{channel.desc}</p>
                    {(connected?.account_name || channelState?.account_name) && (
                      <p className="text-xs text-gray-500 mt-2">계정: {connected?.account_name || channelState?.account_name}</p>
                    )}
                    {connected?.connected_at && (
                      <p className="text-xs text-gray-400 mt-1">연결일: {new Date(connected.connected_at).toLocaleString("ko-KR")}</p>
                    )}
                    {connected?.token_expires_at && (
                      <p className="text-xs text-gray-400 mt-1">만료시각: {new Date(connected.token_expires_at).toLocaleString("ko-KR")}</p>
                    )}
                    {disconnectedReason && (
                      <p className="text-xs text-orange-700 mt-2">상태: {disconnectedReason}</p>
                    )}
                  </div>

                  {channel.enabled ? connected ? (
                    <div className="shrink-0 flex flex-col gap-2">
                      <button onClick={() => void handleConnect(channel.id)} disabled={authLoading === channel.id} className={`inline-flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-lg disabled:opacity-50 ${getTokenHealth(connected.token_expires_at) === "reauth_required" ? "bg-red-600 text-white hover:bg-red-700" : "border border-blue-200 text-blue-600 hover:bg-blue-50"}`}>
                        <PlugZap size={14} />{authLoading === channel.id ? "이동 중..." : getTokenHealth(connected.token_expires_at) === "reauth_required" ? "재연동" : "다시 연결"}
                      </button>
                      <button onClick={() => void handleDisconnect(channel.id)} disabled={authLoading === channel.id} className="inline-flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50">
                        <Unplug size={14} />해제
                      </button>
                    </div>
                  ) : (
                    <button onClick={() => void handleConnect(channel.id)} disabled={authLoading === channel.id} className="shrink-0 inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
                      <PlugZap size={14} />{authLoading === channel.id ? "이동 중..." : "연동하기"}
                    </button>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>

        {channels.length === 0 && (
          <div className="text-center py-8 border-t mt-6">
            <Link2 size={28} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-400">아직 연동된 SNS 채널이 없습니다</p>
            <p className="text-xs text-gray-300 mt-1">위 카드에서 채널별 OAuth 인증을 시작할 수 있습니다</p>
          </div>
        )}
      </div>

      {modalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setModalOpen(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold">클라이언트 수정</h2>
              <button onClick={() => setModalOpen(false)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">이름 *</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">업종 카테고리 *</label>
                <select value={form.industry_category} onChange={(e) => setForm({ ...form, industry_category: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="">선택하세요</option>
                  {INDUSTRY_CATEGORIES.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">브랜드 컬러</label>
                <div className="flex items-center gap-3">
                  <input type="color" value={form.brand_color} onChange={(e) => setForm({ ...form, brand_color: e.target.value })} className="w-10 h-10 rounded-lg border cursor-pointer" />
                  <span className="text-sm text-gray-500">{form.brand_color}</span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">로고 URL</label>
                <input value={form.logo} onChange={(e) => setForm({ ...form, logo: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="https://..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">계정 유형</label>
                <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="brand">브랜드</option>
                  <option value="agency">에이전시</option>
                  <option value="personal">개인</option>
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button onClick={() => setModalOpen(false)} className="flex-1 border rounded-lg py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors">취소</button>
              <button onClick={() => void handleSubmit()} disabled={submitting || !form.name.trim() || !form.industry_category} className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors">{submitting ? "저장 중..." : "저장"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
