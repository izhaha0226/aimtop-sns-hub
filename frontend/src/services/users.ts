import api from "./api"

export const usersService = {
  async me() {
    const res = await api.get("/api/v1/users/me")
    return res.data
  },
  async list() {
    const res = await api.get("/api/v1/users")
    return res.data
  },
  async update(id: string, data: object) {
    const res = await api.put(`/api/v1/users/${id}`, data)
    return res.data
  },
  async updateRole(id: string, role: string, reason?: string) {
    const res = await api.patch(`/api/v1/users/${id}/role`, { role, reason })
    return res.data
  },
  async deactivate(id: string) {
    const res = await api.patch(`/api/v1/users/${id}/deactivate`)
    return res.data
  },
  async activate(id: string) {
    const res = await api.patch(`/api/v1/users/${id}/activate`)
    return res.data
  },
}
