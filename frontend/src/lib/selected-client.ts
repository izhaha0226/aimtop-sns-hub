export const SELECTED_CLIENT_KEY = "selected_client_id"
export const SELECTED_CLIENT_EVENT = "selected-client-changed"

export function getSelectedClientId() {
  if (typeof window === "undefined") return ""
  return localStorage.getItem(SELECTED_CLIENT_KEY) || ""
}

export function setSelectedClientId(clientId: string) {
  if (typeof window === "undefined") return
  const current = localStorage.getItem(SELECTED_CLIENT_KEY) || ""
  if (current === clientId) return
  if (clientId) localStorage.setItem(SELECTED_CLIENT_KEY, clientId)
  else localStorage.removeItem(SELECTED_CLIENT_KEY)
  window.dispatchEvent(new CustomEvent(SELECTED_CLIENT_EVENT, { detail: clientId }))
}
