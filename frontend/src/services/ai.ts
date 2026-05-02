import api from "./api"

export interface GenerateCopyPayload {
  platform: string
  tone?: string
  topic: string
  context?: string
  language?: string
  brand_name?: string
  target_audience?: string
  strategy_keywords?: string[]
  engine?: { provider?: string; model?: string; fallback_enabled?: boolean }
  benchmark?: { client_id?: string; top_k?: number; window_days?: number; platform?: string }
}

export interface GenerateCopyResponse {
  title: string
  body: string
  hashtags: string[]
  cta: string
}

export interface GenerateImagePayload {
  prompt: string
  size?: string
  model?: string
  quality?: "low" | "medium" | "high"
}

export interface GenerateImageResponse {
  image_url: string
  seed: number
  model_used: string
}

export interface ConceptSlide {
  title: string
  body: string
  visual_direction: string
}

export interface ConceptSet {
  concept_name: string
  slides: ConceptSlide[]
}

export interface EngineOverridePayload {
  provider?: string
  model?: string
  fallback_enabled?: boolean
}

export interface GenerateOperationPlanPayload {
  brand_name: string
  product_summary: string
  target_audience?: string
  goals?: string[]
  channels?: string[]
  benchmark_brands?: string[]
  month?: string
  season_context?: string
  budget_level?: string
  notes?: string
  engine?: EngineOverridePayload
}

export interface WeeklyChannelPlan {
  channel: string
  count: number
  formats: string[]
}

export interface WeeklyOperationPlan {
  week: number
  theme: string
  objective: string
  channels: WeeklyChannelPlan[]
}

export interface ChannelOperationPlan {
  channel: string
  monthly_count: number
  recommended_formats: string[]
  role: string
  cadence: string
}

export interface GenerateOperationPlanResponse {
  brand_name: string
  month: string
  strategy_summary: string
  target_insights: string[]
  product_angles: string[]
  seasonal_context: string
  benchmark_source_status: string
  benchmark_notes: string[]
  monthly_volume: Record<string, number>
  total_monthly_count: number
  weekly_plan: WeeklyOperationPlan[]
  channel_plan: ChannelOperationPlan[]
  approval_checklist: string[]
  risks: string[]
  next_actions: string[]
}

export const aiService = {
  async generateCopy(payload: GenerateCopyPayload) {
    const res = await api.post("/api/v1/ai/generate-copy", payload)
    return res.data as GenerateCopyResponse
  },

  async suggestHashtags(topic: string, platform = "instagram", count = 12, engine?: EngineOverridePayload) {
    const res = await api.post("/api/v1/ai/suggest-hashtags", { topic, platform, count, engine })
    return Array.isArray(res.data?.hashtags) ? res.data.hashtags : []
  },

  async generateImage(payload: GenerateImagePayload) {
    const res = await api.post("/api/v1/ai/generate-image", payload)
    return res.data as GenerateImageResponse
  },

  async generateConceptSets(topic: string, brandInfo = "", count = 3, engine?: EngineOverridePayload) {
    const res = await api.post("/api/v1/ai/concept-sets", { topic, brand_info: brandInfo, count, engine })
    return Array.isArray(res.data?.concept_sets) ? (res.data.concept_sets as ConceptSet[]) : []
  },

  async generateOperationPlan(payload: GenerateOperationPlanPayload) {
    const res = await api.post("/api/v1/ai/generate-operation-plan", payload)
    return res.data as GenerateOperationPlanResponse
  },
}
