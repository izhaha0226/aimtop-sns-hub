export interface ReferenceAsset {
  url: string
  asset_type: string
  usage_mode: string
  target_cards: number[]
  memo?: string | null
}

export interface CardStorylineItem {
  card_no: number
  headline: string
  body: string
  visual_brief: string
  cta_or_transition?: string | null
}

export interface VisualOption {
  option_id: string
  label: string
  style_type: string
  prompt: string
  image_url?: string | null
  error?: string | null
}

export interface ContentTopic {
  id: string
  client_id: string
  author_id?: string | null
  title: string
  brief?: string | null
  objective?: string | null
  target_audience?: string | null
  core_message?: string | null
  card_storyline?: CardStorylineItem[] | null
  reference_assets?: ReferenceAsset[] | null
  visual_options?: VisualOption[] | null
  selected_visual_option?: string | null
  shared_visual_prompt?: string | null
  shared_media_urls?: string[] | null
  benchmark_context?: Record<string, unknown> | null
  source_metadata?: Record<string, unknown> | null
  status: string
  created_at: string
  updated_at: string
}

export interface ChannelVariant {
  platform: string
  title: string
  text: string
  hashtags: string[]
  content_id?: string | null
}
