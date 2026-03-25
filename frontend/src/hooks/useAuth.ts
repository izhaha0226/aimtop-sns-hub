"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { LoginRequest } from "@/types/auth";
import * as authService from "@/services/auth";

function storeTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
}

function clearStoredTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

function hasStoredToken(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const userQuery = useQuery({
    queryKey: ["currentUser"],
    queryFn: authService.getMe,
    enabled: hasStoredToken(),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const loginMutation = useMutation({
    mutationFn: (credentials: LoginRequest) =>
      authService.login(credentials),
    onSuccess: (data) => {
      storeTokens(data.access_token, data.refresh_token);
      queryClient.invalidateQueries({ queryKey: ["currentUser"] });
      router.push("/dashboard");
    },
  });

  const handleLogout = useCallback(async () => {
    await authService.logout();
    clearStoredTokens();
    queryClient.clear();
    router.push("/login");
  }, [queryClient, router]);

  return {
    user: userQuery.data ?? null,
    isLoading: userQuery.isLoading,
    isAuthenticated: !!userQuery.data,
    login: loginMutation.mutate,
    loginError: loginMutation.error,
    isLoggingIn: loginMutation.isPending,
    logout: handleLogout,
  };
}
