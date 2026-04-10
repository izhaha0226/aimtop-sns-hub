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
