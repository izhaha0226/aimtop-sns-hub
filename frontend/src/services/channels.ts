import api from "./api"

export const channelsService = {
  async listChannels(clientId: string) {
    const res = await api.get(`/api/v1/clients/${clientId}/channels`)
    return res.data
  },
  async connectChannel(clientId: string, data: { channel_type: string; account_name: string }) {
    const res = await api.post(`/api/v1/clients/${clientId}/channels`, data)
    return res.data
  },
  async disconnectChannel(clientId: string, channelId: string) {
    await api.delete(`/api/v1/clients/${clientId}/channels/${channelId}`)
  },
}
