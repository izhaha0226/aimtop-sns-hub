import api from "./api"

export interface ChannelConnection {
  id: string
  client_id: string
  channel_type: string
  account_name?: string | null
  account_id?: string | null
  display_account_id?: string | null
  display_account_name?: string | null
  facebook_page_id?: string | null
  facebook_page_name?: string | null
  facebook_page_count?: number | null
  channel_choices?: ChannelChoice[]
  selection_required?: boolean
  is_connected: boolean
  connected_at?: string | null
  token_expires_at?: string | null
}

export interface ChannelChoice {
  id: string
  label: string
  platform?: string | null
  page_id?: string | null
  page_name?: string | null
  username?: string | null
  name?: string | null
}

export const AUTO_PUBLISH_SUPPORTED_CHANNELS = ["instagram", "facebook", "linkedin", "youtube", "x", "blog"] as const

export function isAutoPublishSupported(channelType?: string | null) {
  if (!channelType) return false
  return AUTO_PUBLISH_SUPPORTED_CHANNELS.includes(channelType as (typeof AUTO_PUBLISH_SUPPORTED_CHANNELS)[number])
}

export function getAutoPublishBlockReason(channel?: Pick<ChannelConnection, "channel_type" | "account_id" | "facebook_page_id"> | null) {
  if (!channel) return "발행할 채널을 선택해 주세요"
  if (!isAutoPublishSupported(channel.channel_type)) return "현재 연동만 지원, 자동 발행 미지원"
  if (channel.channel_type === "instagram" && !channel.account_id) {
    return "Instagram 발행 계정 ID 없음 · Meta 발행 권한/비즈니스 계정 준비 후 재연동 필요"
  }
  if (channel.channel_type === "facebook" && !(channel.facebook_page_id || channel.account_id)) {
    return "Facebook 페이지 ID 없음 · Facebook 페이지 권한/페이지 연결 확인 후 재연동 필요"
  }
  if (channel.channel_type === "linkedin" && !channel.account_id) {
    return "LinkedIn 작성자 ID 없음 · LinkedIn 계정 재연동 필요"
  }
  return null
}

export function getChannelDisplayAccountId(channel?: Pick<ChannelConnection, "account_id" | "display_account_id"> | null) {
  return channel?.display_account_id || channel?.account_id || null
}

export function getChannelDisplayAccountName(channel?: Pick<ChannelConnection, "account_name" | "display_account_name"> | null) {
  return channel?.display_account_name || channel?.account_name || null
}

export function getChannelPublishAccountId(channel?: Pick<ChannelConnection, "channel_type" | "account_id" | "facebook_page_id"> | null) {
  if (!channel) return null
  if (channel.channel_type === "facebook") return channel.facebook_page_id || channel.account_id || null
  return channel.account_id || null
}

export function isChannelAutoPublishReady(channel?: Pick<ChannelConnection, "channel_type" | "account_id" | "facebook_page_id"> | null) {
  return getAutoPublishBlockReason(channel) === null
}

export type TokenHealth = "healthy" | "expiring" | "reauth_required" | "unknown"

export function getTokenHealth(tokenExpiresAt?: string | null): TokenHealth {
  if (!tokenExpiresAt) return "unknown"
  const expires = new Date(tokenExpiresAt).getTime()
  if (Number.isNaN(expires)) return "unknown"
  const diff = expires - Date.now()
  if (diff <= 0) return "reauth_required"
  if (diff <= 1000 * 60 * 60 * 24 * 7) return "expiring"
  return "healthy"
}

export const channelsService = {
  async list(clientId: string) {
    const res = await api.get(`/api/v1/clients/${clientId}/channels`)
    return Array.isArray(res.data) ? res.data : []
  },

  async selectAccount(clientId: string, channelId: string, selectedId: string) {
    const res = await api.post(`/api/v1/clients/${clientId}/channels/${channelId}/select-account`, {
      selected_id: selectedId,
    })
    return res.data as ChannelConnection
  },
}
