"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"

type LiveCard = {
  key: string
  label: string
  value: string
  meta: string
}

type Props = {
  generatedAt: string
  cards: LiveCard[]
}

const STORAGE_KEY = "agent-monitor-live-cards"
const REFRESH_SECONDS = 15

export function AgentMonitorLivePanel({ generatedAt, cards }: Props) {
  const router = useRouter()
  const [secondsLeft, setSecondsLeft] = useState(REFRESH_SECONDS)
  const [changedKeys] = useState<string[]>(() => {
    if (typeof window === "undefined") return []
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY)
      const previous = raw ? (JSON.parse(raw) as LiveCard[]) : []
      const prevMap = new Map(previous.map((item) => [item.key, item.value]))
      return cards.filter((item) => prevMap.has(item.key) && prevMap.get(item.key) !== item.value).map((item) => item.key)
    } catch {
      return []
    }
  })

  const changedSet = useMemo(() => new Set(changedKeys), [changedKeys])

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cards))
    } catch {
      // noop
    }
  }, [cards])

  useEffect(() => {
    const interval = window.setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          router.refresh()
          return REFRESH_SECONDS
        }
        return prev - 1
      })
    }, 1000)

    return () => window.clearInterval(interval)
  }, [router])

  return (
    <>
      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const changed = changedSet.has(card.key)
          return (
            <div
              key={card.key}
              className={`rounded-2xl border p-5 transition-all duration-700 ${changed ? "border-cyan-300/60 bg-cyan-300/10 shadow-[0_0_0_1px_rgba(34,211,238,0.15)]" : "border-white/10 bg-white/5"}`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm text-slate-400">{card.label}</div>
                {changed && <span className="rounded-full bg-cyan-400/15 px-2 py-0.5 text-[10px] font-semibold text-cyan-200">변경</span>}
              </div>
              <div className="mt-2 text-3xl font-bold text-white">{card.value}</div>
              <div className="mt-1 text-xs text-slate-500">{card.meta}</div>
            </div>
          )
        })}
      </section>

      <section className="mt-4 rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-sm text-slate-300">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="text-slate-400">마지막 갱신</div>
            <div className="mt-1 text-lg font-semibold text-white">{generatedAt}</div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-semibold text-cyan-200">
              {secondsLeft}초 뒤 자동 갱신
            </span>
            {changedKeys.length > 0 && (
              <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-200">
                변경 감지: {changedKeys.join(", ")}
              </span>
            )}
          </div>
        </div>
      </section>
    </>
  )
}
