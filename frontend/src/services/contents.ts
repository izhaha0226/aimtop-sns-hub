import api from "./api"
import type { ContentCreate } from "@/types/content"

export const contentsService = {
  async list(params?: { client_id?: string; status?: string; post_type?: string }) {
    const res = await api.get("/api/v1/contents", { params })
    return res.data
  },
  async create(data: ContentCreate) {
    const res = await api.post("/api/v1/contents", data)
    return res.data
  },
  async get(id: string) {
    const res = await api.get(`/api/v1/contents/${id}`)
    return res.data
  },
  async update(id: string, data: Partial<ContentCreate>) {
    const res = await api.put(`/api/v1/contents/${id}`, data)
    return res.data
  },
  async delete(id: string) {
    await api.delete(`/api/v1/contents/${id}`)
  },
  async requestApproval(id: string) {
    const res = await api.post(`/api/v1/contents/${id}/request-approval`)
    return res.data
  },
  async approveContent(id: string, memo?: string) {
    const res = await api.post(`/api/v1/contents/${id}/approve`, { memo })
    return res.data
  },
  async rejectContent(id: string, memo?: string) {
    const res = await api.post(`/api/v1/contents/${id}/reject`, { memo })
    return res.data
  },
  async publishNow(id: string) {
    const res = await api.post(`/api/v1/contents/${id}/publish-now`)
    return res.data
  },
}
