import api from "./api"

export interface BenchmarkAccountItem {
  id: string
  client_id: string
  platform: string
  handle: string
  source_type: string
  purpose: string
  memo?: string | null
  auto_discovered: boolean
  is_active: boolean
  metadata_json?: Record<string, unknown> | null
  updated_at?: string | null
}

export interface BenchmarkPostItem {
  id: string
  benchmark_account_id: string
  platform: string
  external_post_id?: string | null
  post_url?: string | null
  content_text?: string | null
  hook_text?: string | null
  cta_text?: string | null
  format_type?: string | null
  view_count: number
  like_count: number
  comment_count: number
  share_count: number
  save_count: number
  engagement_rate: number
  benchmark_score: number
  published_at?: string | null
  raw_payload?: Record<string, unknown> | null
}

export interface ActionLanguageProfileItem {
  id?: string | null
  client_id: string
  platform: string
  source_scope: string
  top_hooks_json?: Array<{ pattern: string; count: number }> | null
  top_ctas_json?: Array<{ pattern: string; count: number }> | null
  tone_patterns_json?: Record<string, unknown> | null
  format_patterns_json?: Record<string, unknown> | null
  recommended_prompt_rules?: string | null
  profile_version: number
  updated_at?: string | null
  source_client_id?: string | null
  industry_category?: string | null
  sample_count?: number
}

export interface RefreshAccountResult {
  status: string
  status_label?: string | null
  message: string
  inserted: number
  profile_id?: string | null
  profile_generated?: boolean
  live_supported?: boolean
  platform?: string
  used_placeholder?: boolean
  data_source?: string | null
  data_source_label?: string | null
  view_metric_type?: string | null
  view_metric_label?: string | null
  source_channel_connected?: boolean
  source_channel_platform?: string | null
  source_channel_account_name?: string | null
  source_channel_missing_reason?: string | null
  source_channel_has_token?: boolean
  refreshed_at?: string | null
}

export interface BenchmarkAccountDiagnosticItem {
  account_id: string
  client_id: string
  platform: string
  handle: string
  is_active: boolean
  support_level: string
  support_label: string
  status: string
  status_label?: string | null
  message: string
  live_supported: boolean
  source_channel_connected: boolean
  source_channel_platform?: string | null
  source_channel_account_name?: string | null
  source_channel_missing_reason?: string | null
  source_channel_has_token: boolean
  live_post_count: number
  placeholder_post_count: number
  actual_metric_count: number
  proxy_metric_count: number
  total_post_count: number
  data_source?: string | null
  data_source_label?: string | null
  view_metric_type?: string | null
  view_metric_label?: string | null
  used_placeholder: boolean
  last_refresh_status?: string | null
  last_refresh_status_label?: string | null
  last_refresh_message?: string | null
  last_refresh_inserted?: number
  last_refresh_profile_id?: string | null
  last_refresh_profile_generated?: boolean
  last_refresh_used_placeholder?: boolean
  last_refresh_data_source?: string | null
  last_refresh_data_source_label?: string | null
  last_refresh_view_metric_type?: string | null
  last_refresh_view_metric_label?: string | null
  last_refresh_at?: string | null
}

export const benchmarkingService = {
  async listAccounts(clientId?: string) {
    const res = await api.get("/api/v1/benchmarking/accounts", { params: clientId ? { client_id: clientId } : {} })
    return Array.isArray(res.data) ? (res.data as BenchmarkAccountItem[]) : []
  },

  async createAccount(payload: { client_id: string; platform: string; handle: string; purpose?: string; source_type?: string; memo?: string; metadata_json?: Record<string, unknown> }) {
    const res = await api.post("/api/v1/benchmarking/accounts", payload)
    return res.data as BenchmarkAccountItem
  },

  async updateAccount(id: string, payload: Partial<BenchmarkAccountItem>) {
    const res = await api.patch(`/api/v1/benchmarking/accounts/${id}`, payload)
    return res.data as BenchmarkAccountItem
  },

  async refreshAccount(id: string, topK = 10, windowDays = 30) {
    const res = await api.post(`/api/v1/benchmarking/accounts/${id}/refresh`, null, {
      params: { top_k: topK, window_days: windowDays },
    })
    return res.data as RefreshAccountResult
  },

  async listAccountDiagnostics(clientId: string, platform?: string) {
    const res = await api.get("/api/v1/benchmarking/account-diagnostics", {
      params: {
        client_id: clientId,
        ...(platform ? { platform } : {}),
      },
    })
    return Array.isArray(res.data) ? (res.data as BenchmarkAccountDiagnosticItem[]) : []
  },

  async getTopPosts(clientId: string, platform: string, topK = 10) {
    const res = await api.get("/api/v1/benchmarking/top-posts", {
      params: { client_id: clientId, platform, top_k: topK },
    })
    return Array.isArray(res.data) ? (res.data as BenchmarkPostItem[]) : []
  },

  async getActionProfile(clientId: string, platform: string) {
    const res = await api.get("/api/v1/benchmarking/action-language-profile", {
      params: { client_id: clientId, platform },
    })
    return (res.data || null) as ActionLanguageProfileItem | null
  },
}
