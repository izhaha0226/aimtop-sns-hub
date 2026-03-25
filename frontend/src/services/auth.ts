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
    return api.post("/api/v1/auth/forgot-password", { email })
  },

  async resetPassword(token: string, newPassword: string) {
    return api.post("/api/v1/auth/reset-password", { token, new_password: newPassword })
  },
}
