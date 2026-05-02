import api from "./api"
import type { ChannelVariant, ContentTopic, ReferenceAsset } from "@/types/content-topic"

function normalizeTopic(item: unknown): ContentTopic {
  const topic = (item && typeof item === "object" ? item : {}) as Partial<ContentTopic>
  return {
    id: String(topic.id || ""),
    client_id: String(topic.client_id || ""),
    author_id: topic.author_id || null,
    title: topic.title || "",
    brief: topic.brief || "",
    objective: topic.objective || "awareness",
    target_audience: topic.target_audience || "",
    core_message: topic.core_message || "",
    card_storyline: Array.isArray(topic.card_storyline) ? topic.card_storyline : [],
    reference_assets: Array.isArray(topic.reference_assets) ? topic.reference_assets : [],
    visual_options: Array.isArray(topic.visual_options) ? topic.visual_options : [],
    selected_visual_option: topic.selected_visual_option || null,
    shared_visual_prompt: topic.shared_visual_prompt || null,
    shared_media_urls: Array.isArray(topic.shared_media_urls) ? topic.shared_media_urls.map(String) : [],
    benchmark_context: topic.benchmark_context || null,
    source_metadata: topic.source_metadata || null,
    status: topic.status || "draft",
    created_at: topic.created_at || new Date(0).toISOString(),
    updated_at: topic.updated_at || new Date(0).toISOString(),
  }
}

export const contentTopicsService = {
  async list(params?: { client_id?: string; status?: string }) {
    const res = await api.get("/api/v1/content-topics", { params })
    const items = Array.isArray(res.data) ? res.data : Array.isArray(res.data?.items) ? res.data.items : []
    return items.map(normalizeTopic)
  },
  async create(data: {
    client_id: string
    title: string
    brief?: string
    objective?: string
    target_audience?: string
    core_message?: string
    channels?: string[]
    reference_assets?: ReferenceAsset[]
  }) {
    const res = await api.post("/api/v1/content-topics", data)
    return normalizeTopic(res.data)
  },
  async update(id: string, data: Partial<ContentTopic>) {
    const res = await api.put(`/api/v1/content-topics/${id}`, data)
    return normalizeTopic(res.data)
  },
  async attachReferenceAssets(id: string, assets: ReferenceAsset[]) {
    const res = await api.post(`/api/v1/content-topics/${id}/reference-assets`, { assets })
    return normalizeTopic(res.data)
  },
  async generateStoryline(id: string) {
    const res = await api.post(`/api/v1/content-topics/${id}/generate-storyline`, {})
    return normalizeTopic(res.data)
  },
  async generateVisualOptions(id: string) {
    const res = await api.post(`/api/v1/content-topics/${id}/generate-visual-options`, {}, { timeout: 240000 })
    return normalizeTopic(res.data)
  },
  async selectVisualOption(id: string, option_id: string) {
    const res = await api.post(`/api/v1/content-topics/${id}/select-visual-option`, { option_id })
    return normalizeTopic(res.data)
  },
  async generateCardImages(id: string) {
    const res = await api.post(`/api/v1/content-topics/${id}/generate-card-images`, { model: "fast", size: "1024x1024", quality: "medium" }, { timeout: 360000 })
    return normalizeTopic(res.data)
  },
  async generateChannelVariants(id: string, channels: string[]) {
    const res = await api.post(`/api/v1/content-topics/${id}/generate-channel-variants`, { channels, create_contents: true })
    return (Array.isArray(res.data) ? res.data : []) as ChannelVariant[]
  },
}
