"use client"
import { useState, useEffect, useCallback } from "react"
import { authService } from "@/services/auth"
import { usersService } from "@/services/users"

interface User {
  id: string
  name: string
  email: string
  role: string
  status: string
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchUser() {
      const token = localStorage.getItem("access_token")
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const me = await usersService.me()
        setUser(me)
      } catch {
        localStorage.clear()
      } finally {
        setLoading(false)
      }
    }
    fetchUser()
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    await authService.login(email, password)
    const me = await usersService.me()
    setUser(me)
  }, [])

  const logout = useCallback(async () => {
    await authService.logout()
    setUser(null)
  }, [])

  return {
    user,
    loading,
    login,
    logout,
    isAdmin: user?.role === "admin",
    isApprover: user?.role === "approver" || user?.role === "admin",
  }
}
