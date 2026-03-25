"use client"
import { useQuery } from "@tanstack/react-query"
import { clientsService } from "@/services/clients"

const CLIENTS_KEY = ["clients"] as const

export function useClients() {
  return useQuery({
    queryKey: CLIENTS_KEY,
    queryFn: clientsService.list,
  })
}

export function useClient(id: string) {
  return useQuery({
    queryKey: ["clients", id],
    queryFn: () => clientsService.get(id),
    enabled: !!id,
  })
}
