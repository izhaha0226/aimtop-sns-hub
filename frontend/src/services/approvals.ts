import api from "./api"

export interface ExternalApprovalItem {
  id: string
  content_id: string
  reviewer_name: string
  reviewer_email: string
  status: "pending" | "approved" | "rejected"
  feedback?: string | null
  review_link?: string
  expired?: boolean
  expires_at?: string | null
  responded_at?: string | null
  created_at: string
}

export interface ExternalApprovalDetail extends ExternalApprovalItem {
  content?: {
    title?: string | null
    text?: string | null
    post_type?: string | null
    media_urls?: string[]
  }
}

export interface ExternalApprovalCreatePayload {
  reviewer_name: string
  reviewer_email: string
  expires_hours?: number
}

export const approvalsService = {
  async create(contentId: string, payload: ExternalApprovalCreatePayload) {
    const res = await api.post(`/api/v1/approvals/${contentId}`, payload)
    return res.data?.data as ExternalApprovalItem & { email_sent?: boolean; content_title?: string | null }
  },

  async listForContent(contentId: string) {
    const res = await api.get(`/api/v1/approvals/content/${contentId}`)
    const items = Array.isArray(res.data?.data) ? res.data.data : []
    return items as ExternalApprovalItem[]
  },

  async getByToken(token: string) {
    const res = await api.get(`/api/v1/approvals/review/${token}`)
    return res.data?.data as ExternalApprovalDetail
  },

  async respond(token: string, status: "approved" | "rejected", feedback?: string) {
    const res = await api.post(`/api/v1/approvals/review/${token}/respond`, {
      status,
      feedback: feedback || "",
    })
    return res.data?.data as ExternalApprovalItem
  },
}
