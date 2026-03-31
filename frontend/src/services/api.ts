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
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem("refresh_token")
      if (refresh) {
        try {
          const res = await api.post("/api/v1/auth/refresh", { refresh_token: refresh })
          localStorage.setItem("access_token", res.data.access_token)
          localStorage.setItem("refresh_token", res.data.refresh_token)
          original.headers.Authorization = `Bearer ${res.data.access_token}`
          return api(original)
        } catch {
          localStorage.clear()
          if (typeof window !== "undefined") window.location.href = "/login"
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api
