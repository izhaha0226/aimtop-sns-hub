export type ContentStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "published"
  | "rejected"
  | "failed"
  | "scheduled"

export type PostType =
  | "text"
  | "card_news"
  | "image"
  | "reels"
  | "story"
  | "infographic"
  | "event"
  | "product"

export interface Content {
  id: string
  client_id: string
  client_name?: string
  post_type: PostType
  title: string
  text: string
  hashtags: string[]
  media_urls: string[]
  status: ContentStatus
  author_id: string
  author_name?: string
  memo?: string
  channel_connection_id?: string | null
  platform_post_id?: string | null
  published_url?: string | null
  publish_error?: string | null
  operation_plan_id?: string | null
  source_metadata?: {
    source?: string
    operation_plan_id?: string
    channel?: string
    week?: number
    objective?: string
    format?: string
    sequence?: number
    display_title?: string
    visual_direction?: string
    image_prompt?: string
    channel_action?: string
    benchmark_source_status?: string
    [key: string]: unknown
  } | null
  scheduled_at?: string
  published_at?: string
  created_at: string
  updated_at: string
}

export interface ContentCreate {
  client_id: string
  post_type: PostType
  title: string
  text: string
  hashtags: string[]
  media_urls: string[]
}

export interface ChannelConnection {
  id: string
  client_id: string
  channel_type: string
  account_name: string
  is_active: boolean
  created_at: string
}

export const STATUS_LABELS: Record<ContentStatus, string> = {
  draft: "임시저장",
  pending_approval: "승인 대기",
  approved: "승인됨",
  published: "발행됨",
  rejected: "반려됨",
  failed: "실패",
  scheduled: "예약됨",
}

export const STATUS_COLORS: Record<ContentStatus, string> = {
  draft: "bg-gray-100 text-gray-600",
  pending_approval: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  published: "bg-blue-100 text-blue-700",
  rejected: "bg-red-100 text-red-700",
  failed: "bg-red-100 text-red-700",
  scheduled: "bg-purple-100 text-purple-700",
}

export const POST_TYPE_LABELS: Record<PostType, string> = {
  text: "텍스트",
  card_news: "카드뉴스",
  image: "이미지",
  reels: "릴스",
  story: "스토리",
  infographic: "인포그래픽",
  event: "이벤트",
  product: "제품",
}

export const POST_TYPE_COLORS: Record<PostType, string> = {
  text: "bg-blue-100 text-blue-700",
  card_news: "bg-purple-100 text-purple-700",
  image: "bg-green-100 text-green-700",
  reels: "bg-pink-100 text-pink-700",
  story: "bg-orange-100 text-orange-700",
  infographic: "bg-teal-100 text-teal-700",
  event: "bg-red-100 text-red-700",
  product: "bg-indigo-100 text-indigo-700",
}
