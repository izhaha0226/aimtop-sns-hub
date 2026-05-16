import api from "./api"

export interface ThreadsPersona {
  id: string
  client_id: string
  name: string
  description?: string | null
  tone_keywords_json?: string[] | null
  prohibited_topics_json?: string[] | null
  author_display_name?: string | null
  author_transparency?: string | null
  auth_identity_id?: string | null
  provider_badge_label?: string | null
  is_active: boolean
}

export interface ThreadsTargetRule {
  id: string
  client_id: string
  name: string
  keywords_json?: string[] | null
  competitor_handles_json?: string[] | null
  hashtags_json?: string[] | null
  min_fit_score: number
  daily_like_limit: number
  daily_comment_limit: number
  auto_like_enabled: boolean
  requires_comment_approval: boolean
  is_active: boolean
}

export interface ThreadsDraft {
  id: string
  client_id: string
  persona_id?: string | null
  target_rule_id?: string | null
  action_type: string
  target_post_url?: string | null
  target_author_handle?: string | null
  target_post_text?: string | null
  draft_text?: string | null
  fit_score: number
  safety_score: number
  safety_labels_json?: string[] | null
  status: string
  approval_required: boolean
  provider_badge_label?: string | null
  author_transparency?: string | null
  simulation_status: string
}

export interface ThreadsApproval {
  id: string
  client_id: string
  draft_id: string
  action_type: string
  status: string
  queue_reason?: string | null
  reviewed_at?: string | null
  review_note?: string | null
}

export interface ThreadsActionLog {
  id: string
  client_id: string
  draft_id?: string | null
  approval_id?: string | null
  action_type: string
  status: string
  simulation_status: string
  external_write_enabled: boolean
  message?: string | null
  created_at?: string | null
}

export interface ThreadsLearningEvent {
  id: string
  client_id: string
  action_log_id?: string | null
  event_type: string
  signal_score: number
  outcome?: string | null
  notes?: string | null
}

export interface AuthIdentity {
  id: string
  client_id?: string | null
  provider: string
  display_name?: string | null
  badge_label: string
  is_verified: boolean
}

const asArray = <T,>(value: unknown): T[] => Array.isArray(value) ? (value as T[]) : []

export const threadsAutomationService = {
  async listPersonas(clientId: string) {
    const res = await api.get("/api/v1/threads-automation/personas", { params: { client_id: clientId } })
    return asArray<ThreadsPersona>(res.data)
  },
  async createPersona(payload: Partial<ThreadsPersona> & { client_id: string; name: string }) {
    const res = await api.post("/api/v1/threads-automation/personas", payload)
    return res.data as ThreadsPersona
  },
  async listTargetRules(clientId: string) {
    const res = await api.get("/api/v1/threads-automation/target-rules", { params: { client_id: clientId } })
    return asArray<ThreadsTargetRule>(res.data)
  },
  async createTargetRule(payload: Partial<ThreadsTargetRule> & { client_id: string; name: string }) {
    const res = await api.post("/api/v1/threads-automation/target-rules", payload)
    return res.data as ThreadsTargetRule
  },
  async listDrafts(clientId: string) {
    const res = await api.get("/api/v1/threads-automation/drafts", { params: { client_id: clientId } })
    return asArray<ThreadsDraft>(res.data)
  },
  async createDraft(payload: {
    client_id: string
    persona_id?: string
    target_rule_id?: string
    action_type: string
    target_author_handle?: string
    target_post_text?: string
    draft_text?: string
  }) {
    const res = await api.post("/api/v1/threads-automation/drafts", payload)
    return res.data as ThreadsDraft
  },
  async listApprovals(clientId: string) {
    const res = await api.get("/api/v1/threads-automation/approvals", { params: { client_id: clientId } })
    return asArray<ThreadsApproval>(res.data)
  },
  async updateApproval(id: string, status: "approved" | "rejected" | "queued", review_note?: string) {
    const res = await api.patch(`/api/v1/threads-automation/approvals/${id}/status`, { status, review_note })
    return res.data as ThreadsApproval
  },
  async listActions(clientId: string) {
    const res = await api.get("/api/v1/threads-automation/actions", { params: { client_id: clientId } })
    return asArray<ThreadsActionLog>(res.data)
  },
  async createAction(payload: { client_id: string; draft_id?: string; approval_id?: string; action_type: string }) {
    const res = await api.post("/api/v1/threads-automation/actions", payload)
    return res.data as ThreadsActionLog
  },
  async listLearning(clientId: string) {
    const res = await api.get("/api/v1/threads-automation/learning", { params: { client_id: clientId } })
    return asArray<ThreadsLearningEvent>(res.data)
  },
  async createLearning(payload: { client_id: string; action_log_id?: string; event_type: string; signal_score: number; outcome?: string; notes?: string }) {
    const res = await api.post("/api/v1/threads-automation/learning", payload)
    return res.data as ThreadsLearningEvent
  },
  async listAuthIdentities(clientId: string) {
    const res = await api.get("/api/v1/auth/identities", { params: { client_id: clientId } })
    return asArray<AuthIdentity>(res.data)
  },
}
