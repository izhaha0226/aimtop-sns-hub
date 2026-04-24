"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { TerminalSquare } from "lucide-react"

interface AgentTerminalButtonProps {
  agentKey: string
  agentName: string
}

type OpenTerminalError = {
  type: "unauthorized" | "network" | "unexpected"
  message: string
}

async function requestOpen(agentKey: string) {
  const base = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "")
  const endpoint = `${base}/api/v1/ops/open-terminal`
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null
  const refresh = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null

  const defaultHeaders: Record<string, string> = { "Content-Type": "application/json" }
  if (token) defaultHeaders.Authorization = `Bearer ${token}`

  const callOpenTerminal = async () => {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: defaultHeaders,
      credentials: "include",
      body: JSON.stringify({ agent_key: agentKey }),
    })

    if (res.status === 401) {
      const error: OpenTerminalError = { type: "unauthorized", message: "인증이 필요합니다." }
      throw error
    }

    if (!res.ok) {
      const error: OpenTerminalError = {
        type: "unexpected",
        message: `터미널 실행 요청 실패 (HTTP ${res.status})`,
      }
      throw error
    }

    return res.json()
  }

  try {
    return await callOpenTerminal()
  } catch (error) {
    if (typeof error === "object" && error !== null && (error as OpenTerminalError).type === "unauthorized" && refresh) {
      try {
        const refreshRes = await fetch(`${base}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ refresh_token: refresh }),
        })

        if (refreshRes.ok) {
          const data = (await refreshRes.json()) as { access_token: string; refresh_token: string }
          localStorage.setItem("access_token", data.access_token)
          localStorage.setItem("refresh_token", data.refresh_token)
          defaultHeaders.Authorization = `Bearer ${data.access_token}`
          return callOpenTerminal()
        }
      } catch {
        // refresh 실패
        if (typeof window !== "undefined") {
          localStorage.clear()
        }
        const e: OpenTerminalError = { type: "unauthorized", message: "로그인 세션이 만료되었습니다. 다시 로그인해 주세요." }
        throw e
      }
    }

    throw error
  }
}

function isLocalHostname(hostname: string) {
  if (!hostname) return false
  if (["localhost", "127.0.0.1", "::1"].includes(hostname)) return true
  if (hostname.startsWith("192.168.")) return true
  if (hostname.startsWith("10.")) return true
  if (/^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname)) return true
  return false
}

export function AgentTerminalAutoLauncher() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const launchedRef = useRef<string | null>(null)

  useEffect(() => {
    const agentKey = searchParams.get("open_terminal")
    const hostname = typeof window !== "undefined" ? window.location.hostname : ""
    if (!agentKey || launchedRef.current === agentKey) return

    const next = new URLSearchParams(searchParams.toString())
    next.delete("open_terminal")
    const query = next.toString()

    if (!isLocalHostname(hostname)) {
      launchedRef.current = agentKey
      router.replace(query ? `${pathname}?${query}` : pathname)
      return
    }

    launchedRef.current = agentKey
    void requestOpen(agentKey)
      .catch(() => {
        // 터미널 실행 실패는 로컬 모달/알림으로 처리
      })
      .finally(() => {
        router.replace(query ? `${pathname}?${query}` : pathname)
      })
  }, [pathname, router, searchParams])

  return null
}

export function AgentTerminalButton({ agentKey, agentName }: AgentTerminalButtonProps) {
  const [loading, setLoading] = useState(false)
  const isLocal = useMemo(() => {
    if (typeof window === "undefined") return false
    return isLocalHostname(window.location.hostname)
  }, [])

  const handleClick = async () => {
    if (loading) return

    if (!isLocal) {
      window.alert("터미널은 현재 접속 환경에서는 사용할 수 없습니다. 로컬(127.0.0.1 / localhost)에서만 사용 가능합니다.")
      return
    }

    setLoading(true)
    try {
      await requestOpen(agentKey)
    } catch (error) {
      const message =
        error && typeof error === "object" && "message" in error
          ? String((error as { message: string }).message)
          : `${agentName} 터미널 실행에 실패했습니다. 로그인 상태와 권한을 확인해 주세요.`
      window.alert(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={() => void handleClick()}
      disabled={loading}
      className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <TerminalSquare className="h-3.5 w-3.5" />
      {loading ? "여는 중..." : "터미널"}
    </button>
  )
}
