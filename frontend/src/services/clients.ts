import api from "./api"

export const clientsService = {
  async list() {
    const res = await api.get("/api/v1/clients")
    return res.data
  },
  async get(id: string) {
    const res = await api.get(`/api/v1/clients/${id}`)
    return res.data
  },
  async create(data: { name: string; account_type?: string; brand_color?: string }) {
    const res = await api.post("/api/v1/clients", data)
    return res.data
  },
  async update(id: string, data: object) {
    const res = await api.put(`/api/v1/clients/${id}`, data)
    return res.data
  },
  async delete(id: string) {
    await api.delete(`/api/v1/clients/${id}`)
  },
}
