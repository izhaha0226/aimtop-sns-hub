"use client"

import { useCallback, useEffect, useState } from "react"
import { clientsService } from "@/services/clients"
import { getSelectedClientId, SELECTED_CLIENT_EVENT, setSelectedClientId } from "@/lib/selected-client"

interface Client {
  id: string
  name: string
}

export function useSelectedClient() {
  const [clients, setClients] = useState<Client[]>([])
  const [selectedClientId, setSelectedClientIdState] = useState("")
  const [loading, setLoading] = useState(true)

  const syncSelection = useCallback((clientList: Client[], preferredId?: string) => {
    const requested = preferredId ?? getSelectedClientId()
    const resolved = clientList.find((client) => client.id === requested)?.id || clientList[0]?.id || ""
    setSelectedClientIdState(resolved)
    if (!resolved) return
    if (resolved !== requested) setSelectedClientId(resolved)
  }, [])

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const data = await clientsService.list()
      const clientList = Array.isArray(data) ? data : []
      setClients(clientList)
      syncSelection(clientList)
    } catch {
      setClients([])
      setSelectedClientIdState("")
    } finally {
      setLoading(false)
    }
  }, [syncSelection])

  useEffect(() => {
    reload()
  }, [reload])

  useEffect(() => {
    const handleChange = (event: Event) => {
      const nextId = (event as CustomEvent<string>).detail || getSelectedClientId()
      syncSelection(clients, nextId)
    }
    window.addEventListener(SELECTED_CLIENT_EVENT, handleChange)
    return () => window.removeEventListener(SELECTED_CLIENT_EVENT, handleChange)
  }, [clients, syncSelection])

  const selectClient = useCallback((clientId: string) => {
    setSelectedClientId(clientId)
    syncSelection(clients, clientId)
  }, [clients, syncSelection])

  return {
    clients,
    selectedClientId,
    selectedClient: clients.find((client) => client.id === selectedClientId) || null,
    selectClient,
    loading,
    reload,
  }
}
