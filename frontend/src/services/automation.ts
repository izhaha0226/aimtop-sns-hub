import api from "./api"

export type Capability = {
  platform: string
  label: string
  oauth: boolean
  publish: boolean
  publish_media: string[]
  comment_fetch: boolean
  comment_reply: boolean
  material_variant: boolean
  automation_ready: boolean
  notes: string
  blockers: string[]
}

export type AutomationPolicy = {
  id: string | null
  client_id: string
  platform: string
  enabled: boolean
  require_approval: boolean
  daily_limit: number
  auto_reply_enabled: boolean
  quiet_hours_json?: Record<string, unknown> | null
  config_json?: Record<string, unknown> | null
  capability?: Capability | null
  updated_at?: string | null
}

export type AutomationRun = {
  id: string
  client_id: string
  kind: string
  status: string
  summary_json?: Record<string, unknown> | null
  error?: string | null
  started_at?: string | null
  finished_at?: string | null
}

export type AutomationAction = {
  id: string
  run_id?: string | null
  client_id: string
  platform?: string | null
  action: string
  target_id?: string | null
  ok: boolean
  evidence_json?: Record<string, unknown> | null
  error?: string | null
  created_at?: string | null
}

export type MaterialGenerateResult = {
  ok: boolean
  run: AutomationRun
  topic_id?: string | null
  contents: Array<Record<string, unknown>>
  errors: Array<Record<string, unknown>>
}

export const automationService = {
  async capabilities(): Promise<Capability[]> {
    const res = await api.get("/api/v1/automation/capabilities")
    return Array.isArray(res.data) ? res.data : []
  },

  async listPolicies(clientId: string): Promise<AutomationPolicy[]> {
    const res = await api.get("/api/v1/automation/policies", { params: { client_id: clientId } })
    return Array.isArray(res.data) ? res.data : []
  },

  async upsertPolicy(
    clientId: string,
    platform: string,
    payload: Partial<AutomationPolicy>
  ): Promise<AutomationPolicy> {
    const res = await api.put(`/api/v1/automation/policies/${platform}`, payload, {
      params: { client_id: clientId },
    })
    return res.data
  },

  async generateMaterials(payload: {
    client_id: string
    title: string
    brief?: string
    core_message?: string
    channels: string[]
    require_approval?: boolean
    generate_images?: boolean
    use_fallback_storyline?: boolean
  }): Promise<MaterialGenerateResult> {
    const res = await api.post("/api/v1/automation/materials/generate", payload, { timeout: 190000 })
    return res.data
  },

  async syncComments(clientId: string, platform?: string): Promise<Record<string, unknown>> {
    const res = await api.post(
      "/api/v1/automation/comments/sync",
      { client_id: clientId, platform: platform || null, apply_auto_reply: true },
      { timeout: 120000 }
    )
    return res.data
  },

  async listRuns(clientId: string): Promise<AutomationRun[]> {
    const res = await api.get("/api/v1/automation/runs", { params: { client_id: clientId } })
    return Array.isArray(res.data) ? res.data : []
  },

  async listActions(clientId: string): Promise<AutomationAction[]> {
    const res = await api.get("/api/v1/automation/actions", { params: { client_id: clientId } })
    return Array.isArray(res.data) ? res.data : []
  },
}
