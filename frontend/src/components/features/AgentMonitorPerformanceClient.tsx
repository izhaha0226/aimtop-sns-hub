"use client"

import { useMemo, useState } from "react"

type Agent = {
  key: string
  name: string
  runtime: string
  cpuPercent: number
  ramSharePercent: number
  rssBytes: number
  cacheBytes: number
  storageBytes: number
}

type MetricSpec = {
  key: "cpu" | "ram-share" | "rss" | "cache" | "storage"
  label: string
  description: string
  color: string
}

type Props = {
  agents: Agent[]
  metrics: MetricSpec[]
}

const SORT_STORAGE_KEY = "agent-monitor-performance-sort"

function metricValue(metricKey: MetricSpec["key"], agent: Agent) {
  if (metricKey === "cpu") return agent.cpuPercent
  if (metricKey === "ram-share") return agent.ramSharePercent
  if (metricKey === "rss") return agent.rssBytes
  if (metricKey === "cache") return agent.cacheBytes
  return agent.storageBytes
}

function metricFormat(metricKey: MetricSpec["key"], value: number) {
  if (metricKey === "cpu") return `${value.toFixed(1)}%`
  if (metricKey === "ram-share") return `${value.toFixed(2)}%`
  const units = ["B", "KB", "MB", "GB", "TB"]
  let amount = value
  let index = 0
  while (amount >= 1024 && index < units.length - 1) {
    amount /= 1024
    index += 1
  }
  return `${amount >= 100 ? amount.toFixed(0) : amount.toFixed(1)} ${units[index]}`
}

export function AgentMonitorPerformanceClient({ agents, metrics }: Props) {
  const [sortKey, setSortKey] = useState<string>(() => {
    if (typeof window === "undefined") return metrics[0]?.key || "cpu"
    return window.localStorage.getItem(SORT_STORAGE_KEY) || metrics[0]?.key || "cpu"
  })

  const activeMetric = metrics.find((metric) => metric.key === sortKey) || metrics[0]

  const sortedAgents = useMemo(() => {
    const copied = [...agents]
    copied.sort((a, b) => metricValue(activeMetric.key, b) - metricValue(activeMetric.key, a))
    return copied
  }, [agents, activeMetric])

  const maxByMetric = Object.fromEntries(
    metrics.map((metric) => [metric.key, Math.max(...sortedAgents.map((agent) => metricValue(metric.key, agent)), 1)])
  )

  const handleSort = (key: string) => {
    setSortKey(key)
    try {
      window.localStorage.setItem(SORT_STORAGE_KEY, key)
    } catch {
      // noop
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap gap-2">
        {metrics.map((metric) => {
          const active = metric.key === activeMetric.key
          return (
            <button
              key={metric.key}
              type="button"
              onClick={() => handleSort(metric.key)}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${active ? "border-cyan-300/50 bg-cyan-400/15 text-cyan-200" : "border-white/10 bg-white/5 text-slate-400 hover:bg-white/10 hover:text-slate-200"}`}
            >
              {metric.label} 정렬
            </button>
          )
        })}
      </div>

      <div className="overflow-x-auto">
        <div className="flex min-w-[1040px] items-stretch gap-5">
          {sortedAgents.map((agent) => (
            <div key={agent.key} className="flex-1 rounded-2xl border border-white/10 bg-slate-950/50 p-4">
              <div className="mb-3 text-center">
                <div className="text-sm font-semibold tracking-tight text-white">{agent.name}</div>
                <div className="text-[11px] text-slate-500">{agent.runtime}</div>
              </div>
              <div className="grid grid-cols-5 gap-2.5">
                {metrics.map((metric) => {
                  const raw = metricValue(metric.key, agent)
                  const max = Number(maxByMetric[metric.key]) || 1
                  const ratio = raw / max
                  const height = raw > 0 ? Math.max(14, Math.pow(ratio, 0.78) * 100) : 0
                  return (
                    <div key={`${agent.key}-${metric.key}`} className="grid h-[304px] grid-rows-[34px_212px_28px] items-end">
                      <div className="flex items-end justify-center text-center text-[10px] leading-tight text-slate-300 tabular-nums">
                        {metricFormat(metric.key, raw)}
                      </div>
                      <div className="group relative flex h-full items-end justify-center rounded-t-xl bg-white/5 px-0.5 pb-2">
                        <div
                          className={`w-full rounded-t-lg shadow-[0_0_18px_rgba(255,255,255,0.05)] transition-all duration-300 group-hover:brightness-110 ${metric.color}`}
                          style={{ height: `${height}%` }}
                        />
                        <div className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-48 -translate-x-1/2 rounded-xl border border-white/10 bg-slate-900/95 px-3 py-2 text-left text-[11px] leading-5 text-slate-200 shadow-2xl group-hover:block">
                          <div className="font-semibold text-white">{agent.name} · {metric.label}</div>
                          <div>값: {metricFormat(metric.key, raw)}</div>
                          <div>비교 비율: {(ratio * 100).toFixed(1)}%</div>
                          <div className="text-slate-400">{metric.description}</div>
                        </div>
                      </div>
                      <div className="flex items-end justify-center text-center text-[10px] font-semibold tracking-tight text-slate-200">
                        {metric.label}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {metrics.map((metric) => (
          <div key={metric.key} className={`rounded-2xl border p-4 ${metric.key === activeMetric.key ? "border-cyan-300/40 bg-cyan-400/10" : "border-white/10 bg-white/5"}`}>
            <div className="mb-2 flex items-center gap-2">
              <div className={`inline-block h-2.5 w-2.5 rounded-full ${metric.color}`} />
              <div className="text-sm font-semibold text-white">{metric.label}</div>
            </div>
            <div className="text-xs leading-5 text-slate-400">{metric.description}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
