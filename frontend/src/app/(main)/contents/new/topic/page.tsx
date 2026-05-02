"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, Check, ImagePlus, Loader2, Sparkles, Wand2 } from "lucide-react"
import api from "@/services/api"
import { clientsService } from "@/services/clients"
import { contentTopicsService } from "@/services/content-topics"
import type { ChannelVariant, ContentTopic, ReferenceAsset } from "@/types/content-topic"

const CHANNELS = ["instagram", "facebook", "threads", "x", "linkedin", "kakao", "blog"]
const ASSET_TYPES = ["product", "person", "place", "logo", "brand_style", "competitor_reference", "moodboard", "raw_material"]
const USAGE_MODES = ["reference_only", "must_include", "composite_subject", "style_reference", "do_not_copy_structure"]

type Client = { id: string; name: string }

export default function TopicContentPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [clients, setClients] = useState<Client[]>([])
  const [clientId, setClientId] = useState("")
  const [title, setTitle] = useState("")
  const [brief, setBrief] = useState("")
  const [targetAudience, setTargetAudience] = useState("")
  const [coreMessage, setCoreMessage] = useState("")
  const [channels, setChannels] = useState<string[]>(["instagram", "facebook", "threads"])
  const [assets, setAssets] = useState<ReferenceAsset[]>([])
  const [topic, setTopic] = useState<ContentTopic | null>(null)
  const [variants, setVariants] = useState<ChannelVariant[]>([])
  const [loading, setLoading] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    clientsService.list().then((items) => {
      const normalized = (Array.isArray(items) ? items : items?.items || []).map((item: { id: string; name: string }) => ({ id: item.id, name: item.name }))
      setClients(normalized)
      if (!clientId && normalized[0]?.id) setClientId(normalized[0].id)
    }).catch(console.error)
  }, [clientId])

  function toggleChannel(channel: string) {
    setChannels((prev) => prev.includes(channel) ? prev.filter((item) => item !== channel) : [...prev, channel])
  }

  async function uploadFiles(files: File[]) {
    if (!files.length) return
    setUploading(true)
    try {
      const uploaded: ReferenceAsset[] = []
      for (const file of files) {
        const payload = new FormData()
        payload.append("file", file)
        const res = await api.post("/api/v1/media/upload", payload, { headers: { "Content-Type": "multipart/form-data" } })
        if (res.data?.url) {
          uploaded.push({ url: res.data.url, asset_type: "raw_material", usage_mode: "reference_only", target_cards: [1, 2, 3, 4, 5], memo: file.name })
        }
      }
      if (uploaded.length) setAssets((prev) => [...prev, ...uploaded])
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  function updateAsset(index: number, patch: Partial<ReferenceAsset>) {
    setAssets((prev) => prev.map((asset, idx) => idx === index ? { ...asset, ...patch } : asset))
  }

  async function runStep<T>(label: string, fn: () => Promise<T>) {
    setError(null)
    setLoading(label)
    try {
      return await fn()
    } catch (err) {
      const message = err instanceof Error ? err.message : "처리 중 오류가 발생했습니다"
      setError(message)
      throw err
    } finally {
      setLoading(null)
    }
  }

  async function createTopicAndStoryline() {
    if (!clientId || !title.trim()) {
      setError("클라이언트와 주제는 필수입니다")
      return
    }
    const created = await runStep("5장 카드뉴스 내용 생성 중", async () => {
      const next = await contentTopicsService.create({
        client_id: clientId,
        title,
        brief,
        target_audience: targetAudience,
        core_message: coreMessage,
        channels,
        reference_assets: assets,
      })
      return contentTopicsService.generateStoryline(next.id)
    })
    if (created) setTopic(created)
  }

  async function saveStoryline() {
    if (!topic) return
    const updated = await runStep("스토리라인 저장 중", () => contentTopicsService.update(topic.id, { card_storyline: topic.card_storyline || [] }))
    if (updated) setTopic(updated)
  }

  async function generateVisualOptions() {
    if (!topic) return
    await saveStoryline()
    const updated = await runStep("첫 장 3시안 생성 중", () => contentTopicsService.generateVisualOptions(topic.id))
    if (updated) setTopic(updated)
  }

  async function selectOption(optionId: string) {
    if (!topic) return
    const updated = await runStep("시안 선택 중", () => contentTopicsService.selectVisualOption(topic.id, optionId))
    if (updated) setTopic(updated)
  }

  async function generateImages() {
    if (!topic) return
    const updated = await runStep("선택 스타일로 5장 이미지 생성 중", () => contentTopicsService.generateCardImages(topic.id))
    if (updated) setTopic(updated)
  }

  async function generateVariants() {
    if (!topic) return
    const result = await runStep("채널별 콘텐츠 저장 중", () => contentTopicsService.generateChannelVariants(topic.id, channels))
    if (result) setVariants(result)
  }

  const busy = Boolean(loading)

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><ArrowLeft size={18} /></button>
        <div>
          <h1 className="text-xl font-bold">주제 기반 멀티채널 카드뉴스</h1>
          <p className="text-sm text-gray-500 mt-1">주제 → 첨부/참고/합성 자산 → 5장 내용 → 첫 장 3시안 → 5장 이미지 → 채널별 문구 저장</p>
        </div>
      </div>

      {error && <div className="p-4 rounded-xl bg-red-50 text-red-700 text-sm">{error}</div>}
      {loading && <div className="p-4 rounded-xl bg-blue-50 text-blue-700 text-sm flex items-center gap-2"><Loader2 className="animate-spin" size={16} />{loading}</div>}

      <section className="bg-white rounded-2xl border p-5 space-y-4">
        <div className="flex items-center gap-2 font-semibold"><Sparkles size={18} className="text-blue-600" />1. 주제와 채널</div>
        <div className="grid md:grid-cols-2 gap-4">
          <label className="space-y-1 text-sm font-medium">클라이언트
            <select value={clientId} onChange={(e) => setClientId(e.target.value)} className="w-full border rounded-lg px-3 py-2 font-normal">
              {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium">주제
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: 5월 가정의달 선물 캠페인" className="w-full border rounded-lg px-3 py-2 font-normal" />
          </label>
        </div>
        <textarea value={brief} onChange={(e) => setBrief(e.target.value)} placeholder="브리프/상품/행사/톤앤매너" className="w-full border rounded-lg px-3 py-2 min-h-24" />
        <div className="grid md:grid-cols-2 gap-4">
          <input value={targetAudience} onChange={(e) => setTargetAudience(e.target.value)} placeholder="타깃 고객" className="border rounded-lg px-3 py-2" />
          <input value={coreMessage} onChange={(e) => setCoreMessage(e.target.value)} placeholder="핵심 메시지" className="border rounded-lg px-3 py-2" />
        </div>
        <div className="flex flex-wrap gap-2">
          {CHANNELS.map((channel) => <button key={channel} type="button" onClick={() => toggleChannel(channel)} className={`px-3 py-1.5 rounded-full border text-sm ${channels.includes(channel) ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600"}`}>{channel}</button>)}
        </div>
      </section>

      <section className="bg-white rounded-2xl border p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="font-semibold flex items-center gap-2"><ImagePlus size={18} className="text-blue-600" />2. 첨부/참고/합성 이미지</div>
          <button type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading} className="px-4 py-2 rounded-lg border text-sm hover:border-blue-400 disabled:opacity-50">{uploading ? "업로드 중..." : "파일 업로드"}</button>
          <input ref={fileInputRef} type="file" multiple accept="image/*" className="hidden" onChange={(e) => uploadFiles(Array.from(e.target.files || []))} />
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          {assets.map((asset, index) => (
            <div key={`${asset.url}-${index}`} className="border rounded-xl p-3 space-y-2">
              <img src={asset.url} alt="reference" className="w-full h-36 object-cover rounded-lg bg-gray-50" />
              <div className="grid grid-cols-2 gap-2">
                <select value={asset.asset_type} onChange={(e) => updateAsset(index, { asset_type: e.target.value })} className="border rounded-lg px-2 py-1 text-sm">{ASSET_TYPES.map((item) => <option key={item}>{item}</option>)}</select>
                <select value={asset.usage_mode} onChange={(e) => updateAsset(index, { usage_mode: e.target.value })} className="border rounded-lg px-2 py-1 text-sm">{USAGE_MODES.map((item) => <option key={item}>{item}</option>)}</select>
              </div>
              <input value={asset.target_cards.join(",")} onChange={(e) => updateAsset(index, { target_cards: e.target.value.split(",").map((v) => Number(v.trim())).filter(Boolean) })} className="w-full border rounded-lg px-2 py-1 text-sm" placeholder="target cards: 1,2,3" />
              <input value={asset.memo || ""} onChange={(e) => updateAsset(index, { memo: e.target.value })} className="w-full border rounded-lg px-2 py-1 text-sm" placeholder="메모" />
            </div>
          ))}
          {!assets.length && <div className="text-sm text-gray-500 border rounded-xl p-4">제품/인물/공간/로고/무드보드/벤치마킹 이미지를 업로드하면 각 카드의 visual brief와 이미지 생성 프롬프트에 반영됩니다.</div>}
        </div>
      </section>

      <section className="bg-white rounded-2xl border p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="font-semibold flex items-center gap-2"><Wand2 size={18} className="text-blue-600" />3. 5장 카드뉴스 내용</div>
          <button type="button" disabled={busy} onClick={createTopicAndStoryline} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm disabled:opacity-50">5장 내용 먼저 생성</button>
        </div>
        <div className="grid gap-3">
          {(topic?.card_storyline || []).map((card, idx) => (
            <div key={card.card_no} className="border rounded-xl p-4 grid md:grid-cols-2 gap-3">
              <input value={card.headline} onChange={(e) => setTopic((prev) => prev ? { ...prev, card_storyline: (prev.card_storyline || []).map((item, i) => i === idx ? { ...item, headline: e.target.value } : item) } : prev)} className="border rounded-lg px-3 py-2 font-semibold" />
              <input value={card.cta_or_transition || ""} onChange={(e) => setTopic((prev) => prev ? { ...prev, card_storyline: (prev.card_storyline || []).map((item, i) => i === idx ? { ...item, cta_or_transition: e.target.value } : item) } : prev)} className="border rounded-lg px-3 py-2" />
              <textarea value={card.body} onChange={(e) => setTopic((prev) => prev ? { ...prev, card_storyline: (prev.card_storyline || []).map((item, i) => i === idx ? { ...item, body: e.target.value } : item) } : prev)} className="border rounded-lg px-3 py-2 min-h-24" />
              <textarea value={card.visual_brief} onChange={(e) => setTopic((prev) => prev ? { ...prev, card_storyline: (prev.card_storyline || []).map((item, i) => i === idx ? { ...item, visual_brief: e.target.value } : item) } : prev)} className="border rounded-lg px-3 py-2 min-h-24" />
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white rounded-2xl border p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="font-semibold">4. 첫 장 시안 3개</div>
          <button type="button" disabled={busy || !topic?.card_storyline?.length} onClick={generateVisualOptions} className="px-4 py-2 rounded-lg bg-gray-900 text-white text-sm disabled:opacity-50">실사1/실사2/일러스트 생성</button>
        </div>
        <div className="grid md:grid-cols-3 gap-4">
          {(topic?.visual_options || []).map((option) => (
            <button key={option.option_id} type="button" onClick={() => selectOption(option.option_id)} className={`text-left border rounded-xl p-3 ${topic?.selected_visual_option === option.option_id ? "border-blue-600 ring-2 ring-blue-100" : "hover:border-blue-300"}`}>
              {option.image_url ? <img src={option.image_url} alt={option.label} className="w-full aspect-square object-cover rounded-lg bg-gray-50" /> : <div className="w-full aspect-square rounded-lg bg-gray-100 flex items-center justify-center text-xs text-gray-500">생성 실패/대기</div>}
              <div className="mt-2 font-semibold flex items-center gap-1">{topic?.selected_visual_option === option.option_id && <Check size={14} className="text-blue-600" />}{option.label}</div>
              {option.error && <div className="text-xs text-red-500 mt-1">{option.error}</div>}
            </button>
          ))}
        </div>
      </section>

      <section className="bg-white rounded-2xl border p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="font-semibold">5. 선택 스타일로 5장 이미지 + 채널별 저장</div>
          <div className="flex gap-2">
            <button type="button" disabled={busy || !topic?.selected_visual_option} onClick={generateImages} className="px-4 py-2 rounded-lg border text-sm disabled:opacity-50">5장 이미지 생성</button>
            <button type="button" disabled={busy || !topic?.card_storyline?.length} onClick={generateVariants} className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm disabled:opacity-50">채널별 콘텐츠 저장</button>
          </div>
        </div>
        <div className="grid md:grid-cols-5 gap-3">{(topic?.shared_media_urls || []).map((url, idx) => <img key={url} src={url} alt={`card ${idx + 1}`} className="w-full aspect-square object-cover rounded-lg border bg-gray-50" />)}</div>
        <div className="grid md:grid-cols-2 gap-3">{variants.map((variant) => <div key={variant.platform} className="border rounded-xl p-3"><div className="font-semibold">{variant.platform}</div><div className="text-sm text-gray-700 mt-1 whitespace-pre-wrap line-clamp-5">{variant.text}</div><div className="text-xs text-blue-600 mt-2">content_id: {variant.content_id}</div></div>)}</div>
      </section>
    </div>
  )
}
