import axios from "axios"

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "",
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token")
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {}
    const originalUrl = String(original.url || "")
    const isRefreshRequest = originalUrl.includes("/api/v1/auth/refresh")

    if (error.response?.status === 401) {
      if (isRefreshRequest) {
        if (typeof window !== "undefined") {
          localStorage.clear()
          window.location.href = "/login"
        }
        return Promise.reject(error)
      }

      if (!original._retry) {
        original._retry = true
        const refresh = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null

        if (refresh) {
          try {
            const res = await api.post("/api/v1/auth/refresh", { refresh_token: refresh })
            localStorage.setItem("access_token", res.data.access_token)
            localStorage.setItem("refresh_token", res.data.refresh_token)
            original.headers = original.headers || {}
            original.headers.Authorization = `Bearer ${res.data.access_token}`
            return api(original)
          } catch {
            if (typeof window !== "undefined") {
              localStorage.clear()
              window.location.href = "/login"
            }
          }
        } else if (typeof window !== "undefined") {
          localStorage.clear()
          window.location.href = "/login"
        }
      }
    }

    return Promise.reject(error)
  }
)

export default api
