import api from "./api"

export interface LLMProviderConfigItem {
  id?: string | null
  provider_name: string
  model_name: string
  label: string
  is_active: boolean
  is_default: boolean
  supports_json: boolean
  supports_reasoning: boolean
  max_tokens: number
  timeout_seconds: number
  updated_at?: string | null
}

export interface LLMTaskPolicyItem {
  task_type: string
  routing_mode: string
  primary_provider: string
  primary_model: string
  fallback_provider?: string | null
  fallback_model?: string | null
  top_k: number
  benchmark_window_days: number
  views_weight: number
  engagement_weight: number
  recency_weight: number
  action_language_weight: number
  strict_json_mode: boolean
  fallback_enabled: boolean
  notes?: string | null
  is_active: boolean
  updated_at?: string | null
}

export const adminAISettingsService = {
  async listProviders() {
    const res = await api.get("/api/v1/admin/ai-settings/providers")
    return Array.isArray(res.data) ? (res.data as LLMProviderConfigItem[]) : []
  },

  async updateProvider(id: string, payload: Partial<LLMProviderConfigItem>) {
    const res = await api.put(`/api/v1/admin/ai-settings/providers/${id}`, payload)
    return res.data as LLMProviderConfigItem
  },

  async listTaskPolicies() {
    const res = await api.get("/api/v1/admin/ai-settings/task-policies")
    return Array.isArray(res.data) ? (res.data as LLMTaskPolicyItem[]) : []
  },

  async updateTaskPolicy(taskType: string, payload: Partial<LLMTaskPolicyItem>) {
    const res = await api.put(`/api/v1/admin/ai-settings/task-policies/${taskType}`, payload)
    return res.data as LLMTaskPolicyItem
  },
}
