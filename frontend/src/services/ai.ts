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
}
