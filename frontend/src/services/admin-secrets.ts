import api from "./api"

export interface AdminSecretItem {
  id?: string | null
  secret_key: string
  label: string
  category: string
  description?: string | null
  configured: boolean
  source: "db" | "env" | "empty"
  masked_value: string
  is_active: boolean
  updated_at?: string | null
}

export const adminSecretsService = {
  async list() {
    const res = await api.get("/api/v1/admin/secrets")
    return Array.isArray(res.data) ? (res.data as AdminSecretItem[]) : []
  },

  async update(secretKey: string, payload: { value?: string; is_active?: boolean }) {
    const res = await api.put(`/api/v1/admin/secrets/${secretKey}`, payload)
    return res.data as AdminSecretItem
  },
}
