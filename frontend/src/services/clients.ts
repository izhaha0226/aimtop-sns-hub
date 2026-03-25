import type { Client, ClientCreate } from "@/types/client";
import api from "./api";

export async function getClients(): Promise<Client[]> {
  try {
    const { data } = await api.get<Client[]>("/clients");
    return data;
  } catch (error) {
    console.error("Failed to fetch clients:", error);
    throw new Error("클라이언트 목록을 불러올 수 없습니다.");
  }
}

export async function getClient(id: string): Promise<Client> {
  try {
    const { data } = await api.get<Client>(`/clients/${id}`);
    return data;
  } catch (error) {
    console.error("Failed to fetch client:", error);
    throw new Error("클라이언트 정보를 불러올 수 없습니다.");
  }
}

export async function createClient(payload: ClientCreate): Promise<Client> {
  try {
    const { data } = await api.post<Client>("/clients", payload);
    return data;
  } catch (error) {
    console.error("Failed to create client:", error);
    throw new Error("클라이언트 생성에 실패했습니다.");
  }
}

export async function updateClient(
  id: string,
  payload: Partial<ClientCreate>
): Promise<Client> {
  try {
    const { data } = await api.patch<Client>(`/clients/${id}`, payload);
    return data;
  } catch (error) {
    console.error("Failed to update client:", error);
    throw new Error("클라이언트 수정에 실패했습니다.");
  }
}

export async function deleteClient(id: string): Promise<void> {
  try {
    await api.delete(`/clients/${id}`);
  } catch (error) {
    console.error("Failed to delete client:", error);
    throw new Error("클라이언트 삭제에 실패했습니다.");
  }
}
