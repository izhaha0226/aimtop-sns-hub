"use client"

import { useEffect, useMemo, useState } from "react"
import { AgentTerminalButton } from "@/components/features/AgentTerminalButton"

type Agent = {
  key: string
  name: string
  runtime: string
  status: "running" | "stopped"
  modelLabel: string
  modelDetail: string
  pidText: string
  gatewayState: string
  rssCpuText: string
  uptimeText: string
  sessionText: string
  storageText: string
  homePath: string
  latestActivity: string | null
  contextSummary: string
  memorySummary: string
  notes: string[]
}

type Props = {
  agents: Agent[]
}

const STORAGE_KEY = "agent-monitor-overview"

export function AgentMonitorOverviewClient({ agents }: Props) {
  const [changedMap] = useState<Record<string, string[]>>(() => {
    if (typeof window === "undefined") return {}
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY)
      const previous = raw ? (JSON.parse(raw) as Agent[]) : []
      const prevMap = new Map(previous.map((agent) => [agent.key, agent]))
      const next: Record<string, string[]> = {}
      for (const agent of agents) {
        const prev = prevMap.get(agent.key)
        if (!prev) continue
        const changed: string[] = []
        if (prev.pidText !== agent.pidText) changed.push("pid")
        if (prev.gatewayState !== agent.gatewayState) changed.push("gateway")
        if (prev.rssCpuText !== agent.rssCpuText) changed.push("rssCpu")
        if (prev.uptimeText !== agent.uptimeText) changed.push("uptime")
        if (prev.sessionText !== agent.sessionText) changed.push("sessions")
        if (prev.storageText !== agent.storageText) changed.push("storage")
        if (changed.length > 0) next[agent.key] = changed
      }
      return next
    } catch {
      return {}
    }
  })

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(agents))
    } catch {
      // noop
    }
  }, [agents])

  const changedSets = useMemo(
    () => Object.fromEntries(Object.entries(changedMap).map(([key, values]) => [key, new Set(values)])),
    [changedMap]
  )

  const statClass = (changed: boolean) =>
    `rounded-xl p-3 transition-all duration-700 ${changed ? "bg-cyan-400/10 ring-1 ring-cyan-300/40 shadow-[0_0_0_1px_rgba(34,211,238,0.08)]" : "bg-white/5"}`

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {agents.map((agent) => {
        const changed = changedSets[agent.key] || new Set<string>()
        return (
          <div key={agent.key} className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-lg font-semibold text-white">{agent.name}</div>
                <div className="text-sm text-slate-400">{agent.runtime}</div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${agent.status === "running" ? "bg-emerald-400/15 text-emerald-300" : "bg-rose-400/15 text-rose-300"}`}>
                  {agent.status === "running" ? "RUNNING" : "STOPPED"}
                </span>
                <AgentTerminalButton agentKey={agent.key} agentName={agent.name} />
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-cyan-400/15 bg-cyan-400/10 p-3">
              <div className="text-xs text-cyan-200">현재 모델</div>
              <div className="mt-1 break-all text-sm font-semibold text-white">{agent.modelLabel}</div>
              <div className="mt-1 break-all text-[11px] text-cyan-100/80">{agent.modelDetail}</div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div className={statClass(changed.has("pid"))}>
                <div className="text-slate-500">PID</div>
                <div className="mt-1 font-medium text-white">{agent.pidText}</div>
              </div>
              <div className={statClass(changed.has("gateway"))}>
                <div className="text-slate-500">Gateway</div>
                <div className="mt-1 font-medium text-white">{agent.gatewayState}</div>
              </div>
              <div className={statClass(changed.has("rssCpu"))}>
                <div className="text-slate-500">RSS / CPU</div>
                <div className="mt-1 font-medium text-white tabular-nums">{agent.rssCpuText}</div>
              </div>
              <div className={statClass(changed.has("uptime"))}>
                <div className="text-slate-500">Uptime</div>
                <div className="mt-1 font-medium text-white tabular-nums">{agent.uptimeText}</div>
              </div>
              <div className={statClass(changed.has("sessions"))}>
                <div className="text-slate-500">Sessions</div>
                <div className="mt-1 font-medium text-white tabular-nums">{agent.sessionText}</div>
              </div>
              <div className={statClass(changed.has("storage"))}>
                <div className="text-slate-500">Storage</div>
                <div className="mt-1 font-medium text-white tabular-nums">{agent.storageText}</div>
              </div>
            </div>

            <div className="mt-4 space-y-2 text-xs leading-6 text-slate-400">
              <div>home: {agent.homePath}</div>
              <div>최근 활동: {agent.latestActivity || "-"}</div>
              <div>context: {agent.contextSummary}</div>
              <div>memory: {agent.memorySummary}</div>
            </div>

            {agent.notes.length > 0 && (
              <div className="mt-4 rounded-xl border border-amber-300/15 bg-amber-300/10 p-3 text-xs text-amber-100">
                {agent.notes.join(" · ")}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
