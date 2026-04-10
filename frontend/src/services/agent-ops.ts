import api from "./api"

export const agentOpsService = {
  async openTerminal(agentKey: string) {
    const res = await api.post("/api/v1/ops/open-terminal", {
      agent_key: agentKey,
    })
    return res.data
  },
}
