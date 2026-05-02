"use client"

import { DragEvent, useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, ImagePlus, Lightbulb, Sparkles, Upload, Wand2, Tags, Palette, X } from "lucide-react"
import { contentsService } from "@/services/contents"
import { clientsService } from "@/services/clients"
import { aiService, type ConceptSet } from "@/services/ai"
import { adminAISettingsService, type LLMProviderConfigItem } from "@/services/admin-ai-settings"
import { benchmarkingService, type ActionLanguageProfileItem } from "@/services/benchmarking"
import api from "@/services/api"
import type { PostType } from "@/types/content"
import { Button } from "@/components/common/Button"

type BenchmarkChannel = {
  platform: string
  handle: string
  purpose: string
  memo: string
}

type Client = {
  id: string
  name: string
  industry_category?: string
}

type SlideItem = {
  id: string
  title: string
  body: string
  visual_direction: string
}

const BENCHMARK_PLATFORMS = ["instagram", "facebook", "x", "threads", "tiktok", "youtube", "linkedin"]

interface Props {
  mode: "text" | "card_news"
}

export default function ContentComposer({ mode }: Props) {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [clients, setClients] = useState<Client[]>([])
  const [form, setForm] = useState({
    client_id: "",
    post_type: (mode === "card_news" ? "card_news" : "text") as PostType,
    title: "",
    text: "",
    hashtags: [] as string[],
    media_urls: [] as string[],
  })
  const [hashtagInput, setHashtagInput] = useState("")
  const [benchmarks, setBenchmarks] = useState<BenchmarkChannel[]>([
    { platform: "instagram", handle: "", purpose: "all", memo: "" },
  ])
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [copyLoading, setCopyLoading] = useState(false)
  const [hashtagsLoading, setHashtagsLoading] = useState(false)
  const [imageLoading, setImageLoading] = useState(false)
  const [conceptLoading, setConceptLoading] = useState(false)
  const [conceptSets, setConceptSets] = useState<ConceptSet[]>([])
  const [engineProviders, setEngineProviders] = useState<LLMProviderConfigItem[]>([])
  const [engineProvider, setEngineProvider] = useState("gpt")
  const [engineModel, setEngineModel] = useState("gpt-5.5")
  const [benchmarkTopK, setBenchmarkTopK] = useState(10)
  const [benchmarkWindowDays, setBenchmarkWindowDays] = useState(30)
  const [applyBenchmarkPattern, setApplyBenchmarkPattern] = useState(true)
  const [actionProfile, setActionProfile] = useState<ActionLanguageProfileItem | null>(null)
  const [slides, setSlides] = useState<SlideItem[]>([
    { id: "slide-1", title: "", body: "", visual_direction: "" },
    { id: "slide-2", title: "", body: "", visual_direction: "" },
    { id: "slide-3", title: "", body: "", visual_direction: "" },
  ])

  useEffect(() => {
    clientsService.list().then(setClients).catch(console.error)
    adminAISettingsService.listProviders().then((rows) => {
      setEngineProviders(rows)
      const defaultRow = rows.find((item) => item.is_default) || rows[0]
      if (defaultRow) {
        setEngineProvider(defaultRow.provider_name)
        setEngineModel(defaultRow.model_name)
      }
    }).catch(console.error)
  }, [])

  const pageMeta = useMemo(() => {
    if (mode === "card_news") {
      return {
        title: "카드뉴스 제작",
        subtitle: "벤치마킹 채널과 이미지를 바탕으로 카드뉴스 초안을 작성합니다.",
        placeholder: "슬라이드 흐름, 핵심 메시지, CTA를 입력하세요",
      }
    }
    return {
      title: "텍스트 콘텐츠 작성",
      subtitle: "벤치마킹 참고 계정과 함께 텍스트형 게시물을 빠르게 작성합니다.",
      placeholder: "게시물 본문, 첫 문장 훅, CTA를 입력하세요",
    }
  }, [mode])

  function addHashtag(raw: string) {
    const tags = raw
      .split(/[,\s]+/)
      .map((t) => t.replace(/^#/, "").trim())
      .filter(Boolean)
    if (!tags.length) return
    setForm((prev) => ({ ...prev, hashtags: [...new Set([...prev.hashtags, ...tags])] }))
    setHashtagInput("")
  }

  function removeHashtag(tag: string) {
    setForm((prev) => ({ ...prev, hashtags: prev.hashtags.filter((item) => item !== tag) }))
  }

  function updateBenchmark(index: number, field: keyof BenchmarkChannel, value: string) {
    setBenchmarks((prev) => prev.map((item, idx) => (idx === index ? { ...item, [field]: value } : item)))
  }

  function addBenchmark() {
    if (benchmarks.length >= 5) return
    setBenchmarks((prev) => [...prev, { platform: "instagram", handle: "", purpose: "all", memo: "" }])
  }

  function removeBenchmark(index: number) {
    setBenchmarks((prev) => prev.filter((_, idx) => idx !== index))
  }

  async function uploadFiles(files: File[]) {
    if (!files.length) return
    setUploading(true)
    try {
      const uploadedUrls: string[] = []
      for (const file of files) {
        const payload = new FormData()
        payload.append("file", file)
        const res = await api.post("/api/v1/media/upload", payload, {
          headers: { "Content-Type": "multipart/form-data" },
        })
        if (res.data?.url) uploadedUrls.push(res.data.url)
      }
      if (uploadedUrls.length) {
        setForm((prev) => ({ ...prev, media_urls: [...prev.media_urls, ...uploadedUrls] }))
      }
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  async function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || [])
    if (!files.length) return
    try {
      await uploadFiles(files)
    } catch (error) {
      console.error(error)
    }
  }

  async function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragActive(false)
    const files = Array.from(e.dataTransfer.files || [])
    if (!files.length) return
    try {
      await uploadFiles(files)
    } catch (error) {
      console.error(error)
    }
  }

  function removeMedia(url: string) {
    setForm((prev) => ({ ...prev, media_urls: prev.media_urls.filter((item) => item !== url) }))
  }

  const selectedClient = clients.find((client) => client.id === form.client_id)
  const filteredModels = engineProviders.filter((item) => item.provider_name === engineProvider && item.is_active)

  useEffect(() => {
    if (!form.client_id) return
    benchmarkingService.getActionProfile(form.client_id, mode === "card_news" ? "instagram" : "threads")
      .then(setActionProfile)
      .catch(console.error)
  }, [form.client_id, mode])

  async function handleGenerateCopy() {
    if (!form.title.trim()) return
    setCopyLoading(true)
    try {
      const benchmarkContext = benchmarks
        .filter((item) => item.handle.trim())
        .map((item) => `${item.platform} @${item.handle.replace(/^@/, "")} ${item.purpose} ${item.memo}`.trim())
        .join(" | ")
      const cardNewsContext = mode === "card_news"
        ? slides.map((slide, index) => `슬라이드 ${index + 1}: ${slide.title} / ${slide.body} / ${slide.visual_direction}`).join("\n")
        : ""
      const result = await aiService.generateCopy({
        platform: mode === "card_news" ? "instagram" : "threads",
        tone: "친근한",
        topic: form.title,
        context: [form.text, cardNewsContext, benchmarkContext].filter(Boolean).join("\n"),
        brand_name: selectedClient?.name || "",
        engine: { provider: engineProvider, model: engineModel },
        benchmark: applyBenchmarkPattern ? {
          client_id: form.client_id,
          top_k: benchmarkTopK,
          window_days: benchmarkWindowDays,
          platform: mode === "card_news" ? "instagram" : "threads",
        } : undefined,
      })
      setForm((prev) => ({
        ...prev,
        title: prev.title || result.title,
        text: [result.body, result.cta ? `CTA: ${result.cta}` : ""].filter(Boolean).join("\n\n"),
        hashtags: result.hashtags?.length ? [...new Set([...(prev.hashtags || []), ...result.hashtags])] : prev.hashtags,
      }))
    } catch (error) {
      console.error(error)
    } finally {
      setCopyLoading(false)
    }
  }

  async function handleSuggestHashtags() {
    if (!form.title.trim()) return
    setHashtagsLoading(true)
    try {
      const tags = await aiService.suggestHashtags(form.title, "instagram", 12, { provider: engineProvider, model: engineModel })
      if (tags.length) {
        setForm((prev) => ({ ...prev, hashtags: [...new Set([...(prev.hashtags || []), ...tags])] }))
      }
    } catch (error) {
      console.error(error)
    } finally {
      setHashtagsLoading(false)
    }
  }

  async function handleGenerateImage() {
    const promptBase = [form.title, form.text].filter(Boolean).join(" - ")
    if (!promptBase.trim()) return
    setImageLoading(true)
    try {
      const slidePrompt = mode === "card_news"
        ? slides.map((slide) => [slide.title, slide.body, slide.visual_direction].filter(Boolean).join(", ")).filter(Boolean).join(" | ")
        : ""
      const result = await aiService.generateImage({
        prompt: `${promptBase}${slidePrompt ? ` | ${slidePrompt}` : ""}. ${mode === "card_news" ? "카드뉴스 스타일, 마케팅 비주얼" : "SNS 포스트용 고품질 이미지"}`,
        size: mode === "card_news" ? "1024x1024" : "1024x768",
        model: "gpt-image-2.0",
        quality: mode === "card_news" ? "medium" : undefined,
      })
      if (result.image_url) {
        setForm((prev) => ({ ...prev, media_urls: [...prev.media_urls, result.image_url] }))
      }
    } catch (error) {
      console.error(error)
    } finally {
      setImageLoading(false)
    }
  }

  async function handleGenerateConcepts() {
    if (mode !== "card_news" || !form.title.trim()) return
    setConceptLoading(true)
    try {
      const sets = await aiService.generateConceptSets(form.title, [selectedClient?.name || "", form.text].filter(Boolean).join(" / "), 3, { provider: engineProvider, model: engineModel })
      setConceptSets(sets)
      if (sets[0]?.slides?.length) {
        setSlides(sets[0].slides.map((slide, index) => ({
          id: `slide-${index + 1}`,
          title: slide.title || "",
          body: slide.body || "",
          visual_direction: slide.visual_direction || "",
        })))
      }
    } catch (error) {
      console.error(error)
    } finally {
      setConceptLoading(false)
    }
  }

  async function saveContent(requestApproval: boolean) {
    if (!form.client_id || !form.title.trim()) return
    if (requestApproval) setSubmitting(true)
    else setSaving(true)
    try {
      const benchmarkNote = benchmarks
        .filter((item) => item.handle.trim())
        .map((item) => `@${item.handle.replace(/^@/, "")}(${item.platform}/${item.purpose})${item.memo ? `-${item.memo}` : ""}`)
        .join(", ")

      const slideNote = mode === "card_news"
        ? slides
            .filter((slide) => slide.title.trim() || slide.body.trim() || slide.visual_direction.trim())
            .map((slide, index) => `슬라이드 ${index + 1}\n제목: ${slide.title}\n본문: ${slide.body}\n비주얼: ${slide.visual_direction}`)
            .join("\n\n")
        : ""

      const payload = {
        ...form,
        text: [
          form.text,
          slideNote ? `[슬라이드 구성]\n${slideNote}` : "",
          benchmarkNote ? `[벤치마킹]\n${benchmarkNote}` : "",
        ].filter(Boolean).join("\n\n"),
      }

      const created = await contentsService.create(payload)
      if (requestApproval) {
        await contentsService.requestApproval(created.id)
      }
      router.push("/contents")
    } catch (error) {
      console.error(error)
    } finally {
      setSaving(false)
      setSubmitting(false)
    }
  }

  const isValid = Boolean(form.client_id && form.title.trim())

  return (
    <div className="max-w-4xl">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => router.push("/contents/new")} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-xl font-bold">{pageMeta.title}</h1>
          <p className="text-sm text-gray-500 mt-1">{pageMeta.subtitle}</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div className="bg-white rounded-xl border p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">클라이언트 <span className="text-red-500">*</span></label>
            <select value={form.client_id} onChange={(e) => setForm((prev) => ({ ...prev, client_id: e.target.value }))} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">클라이언트 선택</option>
              {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">제목 <span className="text-red-500">*</span></label>
            <input value={form.title} onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))} placeholder={mode === "card_news" ? "예: 봄 시즌 프로모션 카드뉴스" : "예: 오늘의 운영 팁 텍스트 포스트"} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div>
            <div className="flex items-center justify-between gap-3 mb-1.5">
              <label className="block text-sm font-medium text-gray-700">본문/기획 메모</label>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" onClick={() => void handleGenerateCopy()} loading={copyLoading} disabled={!form.title.trim() || hashtagsLoading || imageLoading || conceptLoading}>
                  <Wand2 size={14} className="mr-1.5" />AI 카피
                </Button>
                <Button variant="secondary" size="sm" onClick={() => void handleSuggestHashtags()} loading={hashtagsLoading} disabled={!form.title.trim() || copyLoading || imageLoading || conceptLoading}>
                  <Tags size={14} className="mr-1.5" />해시태그
                </Button>
                <Button variant="secondary" size="sm" onClick={() => void handleGenerateImage()} loading={imageLoading} disabled={!(form.title.trim() || form.text.trim()) || copyLoading || hashtagsLoading || conceptLoading}>
                  <ImagePlus size={14} className="mr-1.5" />AI 이미지
                </Button>
                {mode === "card_news" && (
                  <Button variant="secondary" size="sm" onClick={() => void handleGenerateConcepts()} loading={conceptLoading} disabled={!form.title.trim() || copyLoading || hashtagsLoading || imageLoading}>
                    <Palette size={14} className="mr-1.5" />컨셉 3종
                  </Button>
                )}
              </div>
            </div>
            <textarea value={form.text} onChange={(e) => setForm((prev) => ({ ...prev, text: e.target.value }))} placeholder={pageMeta.placeholder} rows={mode === "card_news" ? 10 : 8} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
          </div>

          {mode === "card_news" && (
            <div>
              <div className="flex items-center justify-between gap-3 mb-2">
                <label className="block text-sm font-medium text-gray-700">슬라이드 구성</label>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setSlides((prev) => [...prev, { id: `slide-${prev.length + 1}`, title: "", body: "", visual_direction: "" }])}
                >
                  슬라이드 추가
                </Button>
              </div>
              <div className="space-y-3">
                {slides.map((slide, index) => (
                  <div key={slide.id} className="rounded-xl border p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-gray-800">슬라이드 {index + 1}</p>
                      {slides.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setSlides((prev) => prev.filter((item) => item.id !== slide.id))}
                          className="text-gray-400 hover:text-red-500"
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>
                    <input
                      value={slide.title}
                      onChange={(e) => setSlides((prev) => prev.map((item) => item.id === slide.id ? { ...item, title: e.target.value } : item))}
                      placeholder="슬라이드 제목"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <textarea
                      value={slide.body}
                      onChange={(e) => setSlides((prev) => prev.map((item) => item.id === slide.id ? { ...item, body: e.target.value } : item))}
                      placeholder="슬라이드 본문"
                      rows={3}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                    />
                    <input
                      value={slide.visual_direction}
                      onChange={(e) => setSlides((prev) => prev.map((item) => item.id === slide.id ? { ...item, visual_direction: e.target.value } : item))}
                      placeholder="비주얼 방향 (예: 파란 배경, 제품 클로즈업)"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <div className="flex items-center gap-2 mb-1.5 text-sm font-medium text-gray-700">
              <ImagePlus size={16} />
              이미지/영상 삽입
            </div>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              className={`rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors ${dragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-gray-50"}`}
            >
              <p className="text-sm text-gray-600">이미지를 여기로 드래그해서 바로 삽입하거나 업로드 버튼을 누르세요.</p>
              <p className="text-xs text-gray-400 mt-1">카드뉴스 시안, 레퍼런스 이미지, 제품 사진 업로드 가능 · 여러 장 드래그 가능</p>
              <input ref={fileInputRef} type="file" accept="image/*,video/*" multiple onChange={handleFileInput} className="hidden" />
              <button type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading} className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg border bg-white text-sm text-gray-700 hover:border-blue-400 hover:text-blue-600 disabled:opacity-50">
                <Upload size={14} />
                {uploading ? "업로드 중..." : "파일 업로드"}
              </button>
            </div>

            {form.media_urls.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {form.media_urls.map((url) => (
                  <div key={url} className="relative group">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={url} alt="" className="w-24 h-24 object-cover rounded-lg border" />
                    <button type="button" onClick={() => removeMedia(url)} className="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <X size={10} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">해시태그</label>
            {form.hashtags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {form.hashtags.map((tag) => (
                  <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">
                    #{tag}
                    <button type="button" onClick={() => removeHashtag(tag)}><X size={10} /></button>
                  </span>
                ))}
              </div>
            )}
            <input value={hashtagInput} onChange={(e) => setHashtagInput(e.target.value)} onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === ",") {
                e.preventDefault()
                addHashtag(hashtagInput)
              }
            }} onBlur={() => hashtagInput && addHashtag(hashtagInput)} placeholder="해시태그 입력 후 Enter" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div className="flex gap-3 justify-end pt-2">
            <Button variant="secondary" onClick={() => router.push("/contents")}>취소</Button>
            <Button variant="secondary" onClick={() => void saveContent(false)} loading={saving} disabled={!isValid || submitting}>임시저장</Button>
            <Button onClick={() => void saveContent(true)} loading={submitting} disabled={!isValid || saving}>승인 요청</Button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-xl border p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-800 mb-2">
              <Wand2 size={16} />
              엔진 선택 / Top-K 제어
            </div>
            <p className="text-xs text-gray-500 mb-4">대표님 의도 기준으로 Claude/GPT 엔진과 벤치마킹 강도를 여기서 바로 바꿉니다.</p>
            <div className="grid grid-cols-1 gap-3">
              <select value={engineProvider} onChange={(e) => {
                setEngineProvider(e.target.value)
                const next = engineProviders.find((item) => item.provider_name === e.target.value && item.is_active)
                if (next) setEngineModel(next.model_name)
              }} className="w-full border rounded-lg px-3 py-2 text-sm">
                {Array.from(new Set(engineProviders.filter((item) => item.is_active).map((item) => item.provider_name))).map((provider) => (
                  <option key={provider} value={provider}>{provider}</option>
                ))}
              </select>
              <select value={engineModel} onChange={(e) => setEngineModel(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm">
                {filteredModels.map((item) => <option key={`${item.provider_name}-${item.model_name}`} value={item.model_name}>{item.label}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <input value={benchmarkTopK} onChange={(e) => setBenchmarkTopK(Number(e.target.value) || 10)} placeholder="Top-K" className="w-full border rounded-lg px-3 py-2 text-sm" />
                <input value={benchmarkWindowDays} onChange={(e) => setBenchmarkWindowDays(Number(e.target.value) || 30)} placeholder="최근 기간(일)" className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input type="checkbox" checked={applyBenchmarkPattern} onChange={(e) => setApplyBenchmarkPattern(e.target.checked)} />
                상위 포스트 패턴 반영
              </label>
              {actionProfile && (
                <div className="rounded-xl border bg-gray-50 p-3 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-xs text-gray-400">액션 랭귀지 프로필</div>
                    <span className={`px-2 py-1 rounded-full text-[11px] border ${actionProfile.source_scope === "industry_fallback" ? "bg-violet-50 text-violet-700 border-violet-200" : "bg-blue-50 text-blue-700 border-blue-200"}`}>
                      {actionProfile.source_scope === "industry_fallback" ? "업종 fallback" : "직접 학습"}
                    </span>
                    {actionProfile.industry_category && (
                      <span className="px-2 py-1 rounded-full text-[11px] border bg-emerald-50 text-emerald-700 border-emerald-200">
                        업종 {actionProfile.industry_category}
                      </span>
                    )}
                    <span className="px-2 py-1 rounded-full text-[11px] border bg-gray-100 text-gray-700 border-gray-200">
                      샘플 {actionProfile.sample_count || 0}
                    </span>
                  </div>
                  {selectedClient?.industry_category && (
                    <div className="text-[11px] text-gray-500">선택 클라이언트 업종: {selectedClient.industry_category}</div>
                  )}
                  <div className="flex flex-wrap gap-2">{(actionProfile.top_hooks_json || []).slice(0, 3).map((item) => <span key={item.pattern} className="px-2 py-1 rounded-full bg-blue-50 text-blue-700 text-xs">훅 {item.pattern}</span>)}</div>
                  <div className="flex flex-wrap gap-2">{(actionProfile.top_ctas_json || []).slice(0, 3).map((item) => <span key={item.pattern} className="px-2 py-1 rounded-full bg-yellow-50 text-yellow-700 text-xs">CTA {item.pattern}</span>)}</div>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-800 mb-2">
              <Lightbulb size={16} />
              벤치마킹 채널
            </div>
            <p className="text-xs text-gray-500 mb-4">처음 기획할 때 참고할 계정을 넣어두면 나중에 AI/운영전략에 반영하기 쉽게 정리됩니다.</p>
            <div className="space-y-3">
              {benchmarks.map((item, index) => (
                <div key={`${item.platform}-${index}`} className="rounded-xl border p-3 space-y-2 relative">
                  {benchmarks.length > 1 && (
                    <button type="button" onClick={() => removeBenchmark(index)} className="absolute top-2 right-2 text-gray-400 hover:text-red-500">
                      <X size={14} />
                    </button>
                  )}
                  <select value={item.platform} onChange={(e) => updateBenchmark(index, "platform", e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    {BENCHMARK_PLATFORMS.map((platform) => <option key={platform} value={platform}>{platform}</option>)}
                  </select>
                  <input value={item.handle} onChange={(e) => updateBenchmark(index, "handle", e.target.value)} placeholder="@benchmark_account" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  <select value={item.purpose} onChange={(e) => updateBenchmark(index, "purpose", e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="all">전체 벤치마킹</option>
                    <option value="tone">톤앤매너</option>
                    <option value="format">콘텐츠 형식</option>
                    <option value="visual">비주얼/이미지</option>
                  </select>
                  <input value={item.memo} onChange={(e) => updateBenchmark(index, "memo", e.target.value)} placeholder="메모 (선택)" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              ))}
            </div>
            {benchmarks.length < 5 && (
              <button type="button" onClick={addBenchmark} className="mt-3 w-full rounded-xl border-2 border-dashed border-gray-300 py-2 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600">
                벤치마킹 채널 추가 ({benchmarks.length}/5)
              </button>
            )}
          </div>

          {mode === "card_news" && conceptSets.length > 0 && (
            <div className="bg-white rounded-xl border p-5">
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-800 mb-3">
                <Palette size={16} />
                AI 컨셉 제안
              </div>
              <div className="space-y-3">
                {conceptSets.map((set) => (
                  <button
                    key={set.concept_name}
                    type="button"
                    onClick={() => {
                      setSlides(set.slides.map((slide, index) => ({
                        id: `slide-${index + 1}`,
                        title: slide.title || "",
                        body: slide.body || "",
                        visual_direction: slide.visual_direction || "",
                      })))
                      setForm((prev) => ({
                        ...prev,
                        text: set.slides.map((slide, index) => `슬라이드 ${index + 1}. ${slide.title}\n${slide.body}\n비주얼: ${slide.visual_direction}`).join("\n\n"),
                      }))
                    }}
                    className="w-full text-left rounded-xl border p-3 hover:border-blue-400 hover:bg-blue-50 transition-colors"
                  >
                    <p className="text-sm font-semibold text-gray-900">{set.concept_name}</p>
                    <p className="text-xs text-gray-500 mt-1">{set.slides.map((slide) => slide.title).filter(Boolean).join(" · ")}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="bg-blue-50 rounded-xl border border-blue-100 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-800 mb-2">
              <Sparkles size={16} />
              작성 팁
            </div>
            <ul className="text-xs text-blue-700 space-y-2 leading-5">
              <li>• {mode === "card_news" ? "슬라이드 1 훅 / 슬라이드 2~4 정보 / 마지막 CTA 구조로 적어두면 좋습니다." : "첫 문장 훅 + 핵심 메시지 + CTA 순서로 쓰면 승인 전환이 좋습니다."}</li>
              <li>• 이미지 드래그 삽입 후 레퍼런스 설명을 본문에 같이 적으면 팀 전달이 편합니다.</li>
              <li>• 벤치마킹 채널은 운영 목적까지 적어두면 나중에 전략서 생성에 유리합니다.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
