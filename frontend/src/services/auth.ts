import type { InviteRequest, LoginRequest, TokenResponse } from "@/types/auth";
import type { User } from "@/types/user";
import api from "./api";

export async function login(
  credentials: LoginRequest
): Promise<TokenResponse> {
  try {
    const { data } = await api.post<TokenResponse>(
      "/auth/login",
      credentials
    );
    return data;
  } catch (error) {
    console.error("Login failed:", error);
    throw new Error("로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.");
  }
}

export async function refreshToken(
  refresh_token: string
): Promise<TokenResponse> {
  try {
    const { data } = await api.post<TokenResponse>("/auth/refresh", {
      refresh_token,
    });
    return data;
  } catch (error) {
    console.error("Token refresh failed:", error);
    throw new Error("세션이 만료되었습니다. 다시 로그인해주세요.");
  }
}

export async function logout(): Promise<void> {
  try {
    await api.post("/auth/logout");
  } catch (error) {
    console.error("Logout request failed:", error);
  } finally {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  }
}

export async function inviteUser(data: InviteRequest): Promise<void> {
  try {
    await api.post("/auth/invite", data);
  } catch (error) {
    console.error("Invite failed:", error);
    throw new Error("사용자 초대에 실패했습니다.");
  }
}

export async function getMe(): Promise<User> {
  try {
    const { data } = await api.get<User>("/users/me");
    return data;
  } catch (error) {
    console.error("Failed to fetch current user:", error);
    throw new Error("사용자 정보를 불러올 수 없습니다.");
  }
}
