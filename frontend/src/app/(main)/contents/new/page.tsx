"use client"
import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, X, Upload } from "lucide-react"
import { contentsService } from "@/services/contents"
import { clientsService } from "@/services/clients"
import api from "@/services/api"
import type { PostType } from "@/types/content"
import { POST_TYPE_LABELS } from "@/types/content"
import { Button } from "@/components/common/Button"

const POST_TYPES: PostType[] = [
  "text", "card_news", "image", "reels", "story", "infographic", "event", "product",
]

interface Client {
  id: string
  name: string
}

export default function ContentNewPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [clients, setClients] = useState<Client[]>([])
  const [form, setForm] = useState({
    client_id: "",
    post_type: "text" as PostType,
    title: "",
    text: "",
    hashtags: [] as string[],
    media_urls: [] as string[],
  })
  const [hashtagInput, setHashtagInput] = useState("")
  const [uploading, setUploading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    clientsService.list().then(setClients).catch(console.error)
  }, [])

  function addHashtag(raw: string) {
    const tags = raw
      .split(/[,\s]+/)
      .map((t) => t.replace(/^#/, "").trim())
      .filter(Boolean)
    if (tags.length === 0) return
    setForm((prev) => ({
      ...prev,
      hashtags: [...new Set([...prev.hashtags, ...tags])],
    }))
    setHashtagInput("")
  }

  function removeHashtag(tag: string) {
    setForm((prev) => ({ ...prev, hashtags: prev.hashtags.filter((t) => t !== tag) }))
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append("file", file)
      const res = await api.post("/api/v1/media/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      setForm((prev) => ({ ...prev, media_urls: [...prev.media_urls, res.data.url] }))
    } catch (err) {
      console.error(err)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  function removeMedia(url: string) {
    setForm((prev) => ({ ...prev, media_urls: prev.media_urls.filter((u) => u !== url) }))
  }

  async function handleSaveDraft() {
    if (!form.client_id || !form.title) return
    setSaving(true)
    try {
      await contentsService.create(form)
      router.push("/contents")
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  async function handleSubmitApproval() {
    if (!form.client_id || !form.title) return
    setSubmitting(true)
    try {
      const content = await contentsService.create(form)
      await contentsService.requestApproval(content.id)
      router.push("/contents")
    } catch (err) {
      console.error(err)
    } finally {
      setSubmitting(false)
    }
  }

  const isValid = form.client_id && form.title.trim()

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.back()}
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"
        >
          <ArrowLeft size={18} />
        </button>
        <h1 className="text-xl font-bold">새 콘텐츠</h1>
      </div>

      <div className="bg-white rounded-xl border p-6 space-y-5">
        {/* Client selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            클라이언트 <span className="text-red-500">*</span>
          </label>
          <select
            value={form.client_id}
            onChange={(e) => setForm((p) => ({ ...p, client_id: e.target.value }))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">클라이언트 선택</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        {/* Post type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            게시 유형 <span className="text-red-500">*</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {POST_TYPES.map((pt) => (
              <button
                key={pt}
                type="button"
                onClick={() => setForm((p) => ({ ...p, post_type: pt }))}
                className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                  form.post_type === pt
                    ? "border-blue-600 bg-blue-50 text-blue-700 font-medium"
                    : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                {POST_TYPE_LABELS[pt]}
              </button>
            ))}
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            제목 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={form.title}
            onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
            placeholder="콘텐츠 제목을 입력하세요"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Text */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">본문</label>
          <textarea
            value={form.text}
            onChange={(e) => setForm((p) => ({ ...p, text: e.target.value }))}
            placeholder="본문 내용을 입력하세요"
            rows={6}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {/* Hashtags */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">해시태그</label>
          {form.hashtags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {form.hashtags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs"
                >
                  #{tag}
                  <button type="button" onClick={() => removeHashtag(tag)}>
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
          )}
          <input
            type="text"
            value={hashtagInput}
            onChange={(e) => setHashtagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === ",") {
                e.preventDefault()
                addHashtag(hashtagInput)
              }
            }}
            onBlur={() => hashtagInput && addHashtag(hashtagInput)}
            placeholder="해시태그 입력 후 Enter (쉼표로 구분)"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Media upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">미디어</label>
          {form.media_urls.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {form.media_urls.map((url) => (
                <div key={url} className="relative group">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={url}
                    alt=""
                    className="w-20 h-20 object-cover rounded-lg border"
                  />
                  <button
                    type="button"
                    onClick={() => removeMedia(url)}
                    className="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X size={10} />
                  </button>
                </div>
              ))}
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors disabled:opacity-50"
          >
            <Upload size={14} />
            {uploading ? "업로드 중..." : "파일 업로드"}
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 mt-4 justify-end">
        <Button variant="secondary" onClick={() => router.back()}>
          취소
        </Button>
        <Button
          variant="secondary"
          onClick={handleSaveDraft}
          loading={saving}
          disabled={!isValid || submitting}
        >
          임시저장
        </Button>
        <Button
          onClick={handleSubmitApproval}
          loading={submitting}
          disabled={!isValid || saving}
        >
          승인 요청
        </Button>
      </div>
    </div>
  )
}
