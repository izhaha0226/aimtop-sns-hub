"use client"

import { useEffect, useRef, useState } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { TerminalSquare } from "lucide-react"
import { agentOpsService } from "@/services/agent-ops"

interface AgentTerminalButtonProps {
  agentKey: string
  agentName: string
}

async function requestOpen(agentKey: string) {
  return agentOpsService.openTerminal(agentKey)
}

export function AgentTerminalAutoLauncher() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const launchedRef = useRef<string | null>(null)

  useEffect(() => {
    const agentKey = searchParams.get("open_terminal")
    if (!agentKey || launchedRef.current === agentKey) return

    launchedRef.current = agentKey
    void requestOpen(agentKey)
      .catch(() => {
        // api interceptor가 로그인/권한 에러를 처리함
      })
      .finally(() => {
        const next = new URLSearchParams(searchParams.toString())
        next.delete("open_terminal")
        const query = next.toString()
        router.replace(query ? `${pathname}?${query}` : pathname)
      })
  }, [pathname, router, searchParams])

  return null
}

export function AgentTerminalButton({ agentKey, agentName }: AgentTerminalButtonProps) {
  const [loading, setLoading] = useState(false)

  const handleClick = async () => {
    if (loading) return

    if (typeof window !== "undefined" && window.location.hostname === "monitor.aimtop.ai") {
      window.open(`https://sns.aimtop.ai/agent-monitor?open_terminal=${encodeURIComponent(agentKey)}`, "_blank", "noopener,noreferrer")
      return
    }

    setLoading(true)
    try {
      await requestOpen(agentKey)
    } catch {
      window.alert(`${agentName} 터미널 실행에 실패했습니다. 로그인 상태와 권한을 확인해 주세요.`)
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
