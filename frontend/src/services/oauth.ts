import api from "./api"

function extractApiError(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof detail === "string" && detail.trim() ? detail : fallback
}

export const oauthService = {
  async getAuthUrl(platform: string, clientId: string, redirectUri: string, frontendRedirect?: string) {
    try {
      const res = await api.get(`/api/v1/oauth/${platform}/auth-url`, {
        params: {
          client_id: clientId,
          redirect_uri: redirectUri,
          frontend_redirect: frontendRedirect,
        },
      })
      return res.data?.auth_url as string
    } catch (error) {
      throw new Error(extractApiError(error, `${platform} 인증 URL 생성에 실패했습니다.`))
    }
  },

  async disconnect(platform: string, clientId: string) {
    const res = await api.post(`/api/v1/oauth/${platform}/disconnect`, null, {
      params: { client_id: clientId },
    })
    return res.data
  },
}
