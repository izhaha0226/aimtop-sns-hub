import api from "./api"

export interface NotificationItem {
  id: string
  client_id: string
  type: string
  title: string
  message?: string | null
  is_read: boolean
  link_url?: string | null
  created_at: string
}

export const notificationsService = {
  async list(limit = 10) {
    const res = await api.get("/api/v1/notifications", { params: { limit } })
    return Array.isArray(res.data) ? res.data : []
  },

  async unreadCount() {
    const res = await api.get("/api/v1/notifications/unread-count")
    return res.data?.unread_count ?? 0
  },

  async markRead(id: string) {
    return api.put(`/api/v1/notifications/${id}/read`)
  },

  async markAllRead() {
    return api.put("/api/v1/notifications/read-all")
  },
}
