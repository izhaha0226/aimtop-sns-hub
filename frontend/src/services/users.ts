import type { User } from "@/types/user";
import api from "./api";

export async function getUsers(): Promise<User[]> {
  try {
    const { data } = await api.get<User[]>("/users");
    return data;
  } catch (error) {
    console.error("Failed to fetch users:", error);
    throw new Error("사용자 목록을 불러올 수 없습니다.");
  }
}

export async function getUser(id: string): Promise<User> {
  try {
    const { data } = await api.get<User>(`/users/${id}`);
    return data;
  } catch (error) {
    console.error("Failed to fetch user:", error);
    throw new Error("사용자 정보를 불러올 수 없습니다.");
  }
}

export async function updateUser(
  id: string,
  updates: Partial<User>
): Promise<User> {
  try {
    const { data } = await api.patch<User>(`/users/${id}`, updates);
    return data;
  } catch (error) {
    console.error("Failed to update user:", error);
    throw new Error("사용자 정보 수정에 실패했습니다.");
  }
}

export async function deactivateUser(id: string): Promise<void> {
  try {
    await api.patch(`/users/${id}`, { status: "inactive" });
  } catch (error) {
    console.error("Failed to deactivate user:", error);
    throw new Error("사용자 비활성화에 실패했습니다.");
  }
}
