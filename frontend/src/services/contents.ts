import api from "./api"
import type { Content, ContentCreate } from "@/types/content"

function normalizeContent(content: unknown): Content {
  const item = (content && typeof content === "object" ? content : {}) as Partial<Content>
  return {
    id: String(item.id || ""),
    client_id: String(item.client_id || ""),
    client_name: item.client_name || undefined,
    post_type: (item.post_type || "text") as Content["post_type"],
    title: item.title || "",
    text: item.text || "",
    hashtags: Array.isArray(item.hashtags) ? item.hashtags.map(String) : [],
    media_urls: Array.isArray(item.media_urls) ? item.media_urls.map(String) : [],
    status: (item.status || "draft") as Content["status"],
    author_id: String(item.author_id || ""),
    author_name: item.author_name || undefined,
    memo: item.memo || undefined,
    channel_connection_id: item.channel_connection_id || null,
    published_url: item.published_url || null,
    publish_error: item.publish_error || null,
    scheduled_at: item.scheduled_at || undefined,
    published_at: item.published_at || undefined,
    created_at: item.created_at || new Date(0).toISOString(),
    updated_at: item.updated_at || new Date(0).toISOString(),
  }
}

export const contentsService = {
  async list(params?: { client_id?: string; status?: string; post_type?: string }) {
    const res = await api.get("/api/v1/contents", { params })
    const items = Array.isArray(res.data) ? res.data : Array.isArray(res.data?.items) ? res.data.items : []
    return items.map(normalizeContent)
  },
  async create(data: ContentCreate) {
    const res = await api.post("/api/v1/contents", data)
    return normalizeContent(res.data)
  },
  async get(id: string) {
    const res = await api.get(`/api/v1/contents/${id}`)
    return normalizeContent(res.data)
  },
  async update(id: string, data: Partial<ContentCreate>) {
    const res = await api.put(`/api/v1/contents/${id}`, data)
    return normalizeContent(res.data)
  },
  async delete(id: string) {
    await api.delete(`/api/v1/contents/${id}`)
  },
  async requestApproval(id: string) {
    const res = await api.post(`/api/v1/contents/${id}/request-approval`)
    return normalizeContent(res.data)
  },
  async approveContent(id: string, memo?: string) {
    const res = await api.post(`/api/v1/contents/${id}/approve`, { memo })
    return normalizeContent(res.data)
  },
  async rejectContent(id: string, memo?: string) {
    const res = await api.post(`/api/v1/contents/${id}/reject`, { memo })
    return normalizeContent(res.data)
  },
  async publishNow(id: string, channelConnectionId?: string) {
    const res = await api.post(`/api/v1/contents/${id}/publish-now`, null, {
      params: channelConnectionId ? { channel_connection_id: channelConnectionId } : undefined,
    })
    return normalizeContent(res.data)
  },
  async schedule(id: string, scheduledAt: string, channelConnectionId: string) {
    const res = await api.post(`/api/v1/contents/${id}/schedule`, {
      scheduled_at: scheduledAt,
      channel_connection_id: channelConnectionId,
    })
    return res.data
  },
}
