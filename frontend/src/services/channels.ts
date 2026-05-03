import api from "./api"

export interface ChannelConnection {
  id: string
  client_id: string
  channel_type: string
  account_name?: string | null
  account_id?: string | null
  is_connected: boolean
  connected_at?: string | null
  token_expires_at?: string | null
}

export const AUTO_PUBLISH_SUPPORTED_CHANNELS = ["instagram", "youtube", "x", "blog"] as const

export function isAutoPublishSupported(channelType?: string | null) {
  if (!channelType) return false
  return AUTO_PUBLISH_SUPPORTED_CHANNELS.includes(channelType as (typeof AUTO_PUBLISH_SUPPORTED_CHANNELS)[number])
}

export function getAutoPublishBlockReason(channel?: Pick<ChannelConnection, "channel_type" | "account_id"> | null) {
  if (!channel) return "발행할 채널을 선택해 주세요"
  if (!isAutoPublishSupported(channel.channel_type)) return "현재 연동만 지원, 자동 발행 미지원"
  if (channel.channel_type === "instagram" && !channel.account_id) {
    return "Instagram 발행 계정 ID 없음 · Meta 발행 권한/비즈니스 계정 준비 후 재연동 필요"
  }
  return null
}

export function isChannelAutoPublishReady(channel?: Pick<ChannelConnection, "channel_type" | "account_id"> | null) {
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
}
