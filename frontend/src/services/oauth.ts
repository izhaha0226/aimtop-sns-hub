import api from "./api"

export const oauthService = {
  async getAuthUrl(platform: string, clientId: string, redirectUri: string, frontendRedirect?: string) {
    const res = await api.get(`/api/v1/oauth/${platform}/auth-url`, {
      params: {
        client_id: clientId,
        redirect_uri: redirectUri,
        frontend_redirect: frontendRedirect,
      },
    })
    return res.data?.auth_url as string
  },

  async disconnect(platform: string, clientId: string) {
    const res = await api.post(`/api/v1/oauth/${platform}/disconnect`, null, {
      params: { client_id: clientId },
    })
    return res.data
  },
}
