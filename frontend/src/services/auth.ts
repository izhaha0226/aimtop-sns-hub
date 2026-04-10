import api from "./api"

export const authService = {
  async login(email: string, password: string) {
    const res = await api.post("/api/v1/auth/login", { email, password })
    localStorage.setItem("access_token", res.data.access_token)
    localStorage.setItem("refresh_token", res.data.refresh_token)
    return res.data
  },

  async logout() {
    await api.post("/api/v1/auth/logout").catch(() => {})
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
  },

  async forgotPassword(email: string) {
    const res = await api.post("/api/v1/auth/forgot-password", { email })
    return res.data
  },

  async resetPassword(token: string, newPassword: string) {
    const res = await api.post("/api/v1/auth/reset-password", { token, new_password: newPassword })
    return res.data
  },

  async acceptInvite(token: string, password: string) {
    const res = await api.post("/api/v1/auth/accept-invite", { token, password })
    localStorage.setItem("access_token", res.data.access_token)
    localStorage.setItem("refresh_token", res.data.refresh_token)
    return res.data
  },
}
