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
}
