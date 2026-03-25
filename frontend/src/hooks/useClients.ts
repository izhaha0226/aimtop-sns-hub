"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { ClientCreate } from "@/types/client";
import * as clientsService from "@/services/clients";

const CLIENTS_KEY = ["clients"] as const;

function clientKey(id: string) {
  return ["clients", id] as const;
}

export function useClients() {
  return useQuery({
    queryKey: CLIENTS_KEY,
    queryFn: clientsService.getClients,
  });
}

export function useClient(id: string) {
  return useQuery({
    queryKey: clientKey(id),
    queryFn: () => clientsService.getClient(id),
    enabled: !!id,
  });
}

export function useCreateClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ClientCreate) => clientsService.createClient(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CLIENTS_KEY });
    },
  });
}

export function useUpdateClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Partial<ClientCreate>;
    }) => clientsService.updateClient(id, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: CLIENTS_KEY });
      queryClient.invalidateQueries({
        queryKey: clientKey(variables.id),
      });
    },
  });
}

export function useDeleteClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => clientsService.deleteClient(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CLIENTS_KEY });
    },
  });
}
