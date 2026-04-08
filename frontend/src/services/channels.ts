import api from "./api"

export interface ChannelConnection {
  id: string
  client_id: string
  channel_type: string
  account_name?: string | null
  account_id?: string | null
  is_connected: boolean
}

export const channelsService = {
  async list(clientId: string) {
    const res = await api.get(`/api/v1/clients/${clientId}/channels`)
    return Array.isArray(res.data) ? res.data : []
  },
}
