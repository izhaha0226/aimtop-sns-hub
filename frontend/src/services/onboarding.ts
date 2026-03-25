import api from "./api"

export const onboardingService = {
  async get(clientId: string) {
    const res = await api.get(`/api/v1/clients/${clientId}/onboarding`)
    return res.data
  },
  async step1(clientId: string, account_type: string) {
    const res = await api.post(`/api/v1/clients/${clientId}/onboarding/step1`, { account_type })
    return res.data
  },
  async step2(clientId: string, data: object) {
    const res = await api.post(`/api/v1/clients/${clientId}/onboarding/step2`, data)
    return res.data
  },
  async step3(clientId: string, selected_channels: string[]) {
    const res = await api.post(`/api/v1/clients/${clientId}/onboarding/step3`, { selected_channels })
    return res.data
  },
  async step4(clientId: string, benchmark_channels: object[]) {
    const res = await api.post(`/api/v1/clients/${clientId}/onboarding/step4`, { benchmark_channels })
    return res.data
  },
  async complete(clientId: string) {
    const res = await api.post(`/api/v1/clients/${clientId}/onboarding/complete`)
    return res.data
  },
}
