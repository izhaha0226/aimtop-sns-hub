import api from "./api"
import type { GenerateOperationPlanPayload, GenerateOperationPlanResponse } from "./ai"

export type OperationPlanStatus = "draft" | "pending_approval" | "approved" | "rejected"

export interface OperationPlanRecord {
  id: string
  client_id: string | null
  author_id: string | null
  approver_id: string | null
  brand_name: string
  month: string
  status: OperationPlanStatus
  strategy_summary: string | null
  request_payload: GenerateOperationPlanPayload | null
  plan_payload: GenerateOperationPlanResponse | null
  approval_memo: string | null
  rejected_reason: string | null
  submitted_at: string | null
  approved_at: string | null
  rejected_at: string | null
  created_at: string
  updated_at: string
}

export interface OperationPlanListResponse {
  items: OperationPlanRecord[]
  total: number
}

export interface OperationPlanDraftRecord {
  id: string
  client_id: string
  author_id: string | null
  post_type: string
  title: string | null
  text: string | null
  media_urls: unknown[] | null
  hashtags: unknown[] | null
  status: string
  channel_connection_id: string | null
  operation_plan_id: string | null
  source_metadata: {
    channel?: string
    week?: number
    channel_action?: "manual_required" | "token_check_required"
    benchmark_source_status?: string
    safety_notes?: string[]
    [key: string]: unknown
  } | null
  platform_post_id: string | null
  published_url: string | null
  publish_error: string | null
  scheduled_at: string | null
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface OperationPlanDraftsResponse {
  operation_plan_id: string
  items: OperationPlanDraftRecord[]
  total: number
  manual_required_count: number
  token_check_required_count: number
}

export const operationPlansService = {
  async list(params?: { client_id?: string; status?: OperationPlanStatus }) {
    const res = await api.get("/api/v1/operation-plans", { params })
    return res.data as OperationPlanListResponse
  },

  async create(payload: {
    client_id?: string | null
    brand_name: string
    month: string
    strategy_summary?: string | null
    request_payload?: GenerateOperationPlanPayload | null
    plan_payload: GenerateOperationPlanResponse
  }) {
    const res = await api.post("/api/v1/operation-plans", payload)
    return res.data as OperationPlanRecord
  },

  async submit(id: string, memo?: string) {
    const res = await api.post(`/api/v1/operation-plans/${id}/submit`, { memo })
    return res.data as OperationPlanRecord
  },

  async approve(id: string, memo?: string) {
    const res = await api.post(`/api/v1/operation-plans/${id}/approve`, { memo })
    return res.data as OperationPlanRecord
  },

  async reject(id: string, memo?: string) {
    const res = await api.post(`/api/v1/operation-plans/${id}/reject`, { memo })
    return res.data as OperationPlanRecord
  },

  async generateDrafts(id: string) {
    const res = await api.post(`/api/v1/operation-plans/${id}/generate-drafts`)
    return res.data as OperationPlanDraftsResponse
  },
}
