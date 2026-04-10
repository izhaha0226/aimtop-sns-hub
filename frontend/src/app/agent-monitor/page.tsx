import { collectFleetMetrics, agentMonitorFormatters } from "@/lib/agent-monitor"
import { AgentTerminalAutoLauncher } from "@/components/features/AgentTerminalButton"
import { AgentMonitorLivePanel } from "@/components/features/AgentMonitorLivePanel"
import { AgentMonitorOverviewClient } from "@/components/features/AgentMonitorOverviewClient"
import { AgentMonitorPerformanceClient } from "@/components/features/AgentMonitorPerformanceClient"

export const dynamic = "force-dynamic"
export const metadata = {
  title: "Agent Monitor | AimTop",
  description: "Running agent monitoring dashboard",
}

const { formatBytes, formatDuration } = agentMonitorFormatters

type MetricSpec = {
  key: "cpu" | "ram-share" | "rss" | "cache" | "storage"
  label: string
  description: string
  color: string
}

export default async function AgentMonitorPage() {
  const fleet = collectFleetMetrics()
  const metricSpecs: MetricSpec[] = [
    {
      key: "cpu",
      label: "CPU",
      description: "현재 프로세스가 점유 중인 CPU 비율입니다. 순간 부하를 비교할 때 가장 직관적인 항목입니다.",
      color: "bg-sky-400",
    },
    {
      key: "ram-share",
      label: "RAM",
      description: "전체 시스템 메모리 대비 각 에이전트 RSS가 차지하는 비율입니다. 대표님이 요청한 RAM 점유율 비교용 핵심 지표입니다.",
      color: "bg-fuchsia-400",
    },
    {
      key: "rss",
      label: "RSS",
      description: "실제로 물리 메모리에 상주 중인 프로세스 메모리 크기입니다. 말 그대로 지금 잡아먹고 있는 메모리라고 보시면 됩니다.",
      color: "bg-cyan-400",
    },
    {
      key: "cache",
      label: "Cache",
      description: "에이전트 홈폴더 내부 cache/.cache 기준 캐시 점유량입니다. 반복 실행 누적 흔적을 보기 좋습니다.",
      color: "bg-amber-400",
    },
    {
      key: "storage",
      label: "Storage",
      description: "에이전트 홈폴더 전체 디스크 사용량입니다. 세션, 로그, DB, 캐시까지 포함한 총 footprint 비교용입니다.",
      color: "bg-emerald-400",
    },
  ]

  const liveCards = [
    { key: "activeAgents", label: "활성 에이전트", value: `${fleet.activeAgents} / ${fleet.agents.length}`, meta: "프로세스 + 최근 로그 기준" },
    { key: "liveGateways", label: "라이브 게이트웨이", value: `${fleet.liveGateways}`, meta: "연결됨/실행중 상태" },
    { key: "totalRssBytes", label: "총 RSS", value: formatBytes(fleet.totalRssBytes), meta: "프로세스 메모리 합" },
    { key: "totalStorageBytes", label: "총 스토리지", value: formatBytes(fleet.totalStorageBytes), meta: "agent home path 합산" },
  ]

  const overviewAgents = fleet.agents.map((agent) => ({
    key: agent.key,
    name: agent.name,
    runtime: agent.runtime,
    status: agent.status,
    modelLabel: agent.modelLabel,
    modelDetail: agent.modelDetail,
    pidText: agent.pidText,
    gatewayState: agent.gatewayState,
    rssCpuText: `${formatBytes(agent.rssBytes)} / ${agent.cpuPercent.toFixed(1)}%`,
    uptimeText: formatDuration(agent.uptimeSeconds),
    sessionText: agent.sessionCount.toLocaleString(),
    storageText: formatBytes(agent.storageBytes),
    homePath: agent.homePath,
    latestActivity: agent.latestActivity,
    contextSummary: agent.contextSummary,
    memorySummary: agent.memorySummary,
    notes: agent.notes,
  }))

  const performanceAgents = fleet.agents.map((agent) => ({
    key: agent.key,
    name: agent.name,
    runtime: agent.runtime,
    cpuPercent: agent.cpuPercent,
    ramSharePercent: agent.ramSharePercent,
    rssBytes: agent.rssBytes,
    cacheBytes: agent.cacheBytes,
    storageBytes: agent.storageBytes,
  }))

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <AgentTerminalAutoLauncher />
      <div className="mx-auto max-w-7xl px-6 py-10">
        <section className="rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 p-8 shadow-2xl">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-3 inline-flex rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-semibold tracking-wide text-cyan-300">
                실측 기반 Agent Fleet Dashboard
              </div>
              <h1 className="text-4xl font-bold tracking-tight">Agent Monitor</h1>
              <p className="mt-4 max-w-4xl text-sm leading-7 text-slate-300">
                현재 머신에서 감지된 실행 에이전트를 실제 프로세스 / 로그 / 세션 / 설정 파일 기준으로 자동 집계해 보여줍니다.
                하드코딩 목록이 아니라 monitor 자체가 홈 디렉터리와 실행 프로세스를 스캔해서 등록합니다.
              </p>
            </div>
          </div>
        </section>

        <AgentMonitorLivePanel key={fleet.generatedAt} generatedAt={fleet.generatedAt} cards={liveCards} />

        <section className="mt-6 grid gap-6 xl:grid-cols-[1.45fr_0.9fr]">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Agent Overview</h2>
              <div className="text-xs text-slate-500">프로세스 / 모델 / 게이트웨이 / 세션</div>
            </div>
            <AgentMonitorOverviewClient agents={overviewAgents} />
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-xl font-semibold">Warnings</h2>
                <div className="text-xs text-slate-500">실측 기반 경고</div>
              </div>
              <div className="space-y-3">
                {fleet.warnings.length > 0 ? (
                  fleet.warnings.map((warning) => (
                    <div key={warning} className="rounded-2xl border border-amber-300/15 bg-amber-300/10 p-4 text-sm text-amber-100">
                      {warning}
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-emerald-300/15 bg-emerald-300/10 p-4 text-sm text-emerald-100">
                    현재 즉시 경고 없음
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-xl font-semibold">Automation Snapshot</h2>
                <div className="text-xs text-slate-500">delegate / cron / error</div>
              </div>
              <div className="space-y-4 text-sm">
                {fleet.agents.map((agent) => (
                  <div key={agent.key} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                    <div className="flex items-center justify-between">
                      <div className="font-medium text-white">{agent.name}</div>
                      <div className="text-xs text-slate-500">{agent.runtime}</div>
                    </div>
                    <div className="mt-2 text-[11px] text-cyan-200 break-all">{agent.modelLabel}</div>
                    <div className="mt-3 grid grid-cols-3 gap-3 text-center">
                      <div className="rounded-xl bg-white/5 p-3">
                        <div className="text-xs text-slate-500">Cron</div>
                        <div className="mt-1 text-lg font-semibold text-white">{agent.cronCount}</div>
                      </div>
                      <div className="rounded-xl bg-white/5 p-3">
                        <div className="text-xs text-slate-500">Delegate traces</div>
                        <div className="mt-1 text-lg font-semibold text-white">{agent.delegateTraceCount}</div>
                      </div>
                      <div className="rounded-xl bg-white/5 p-3">
                        <div className="text-xs text-slate-500">Recent errors</div>
                        <div className="mt-1 text-lg font-semibold text-white">{agent.gatewayErrors}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mt-6 rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">Performance Comparison</h2>
              <div className="mt-1 text-xs text-slate-500">세로 멀티 막대형 · 5개 대표 성능 항목을 한눈에 비교</div>
            </div>
            <div className="text-xs text-slate-500">CPU / RAM / RSS / Cache / Storage</div>
          </div>
          <AgentMonitorPerformanceClient agents={performanceAgents} metrics={metricSpecs} />
        </section>

        <section className="mt-6 rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-xl font-semibold">Storage Breakdown</h2>
            <div className="text-xs text-slate-500">sessions / logs / db</div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-slate-500">
                <tr>
                  <th className="pb-3 pr-4">Agent</th>
                  <th className="pb-3 pr-4">Model</th>
                  <th className="pb-3 pr-4">Sessions</th>
                  <th className="pb-3 pr-4">Logs</th>
                  <th className="pb-3 pr-4">DB</th>
                  <th className="pb-3 pr-4">Total</th>
                </tr>
              </thead>
              <tbody>
                {fleet.agents.map((agent) => (
                  <tr key={agent.key} className="border-t border-white/10 text-slate-200 align-top">
                    <td className="py-3 pr-4 font-medium text-white">{agent.name}</td>
                    <td className="py-3 pr-4 text-xs break-all text-cyan-200">{agent.modelLabel}</td>
                    <td className="py-3 pr-4">{formatBytes(agent.sessionBytes)}</td>
                    <td className="py-3 pr-4">{formatBytes(agent.logBytes)}</td>
                    <td className="py-3 pr-4">{formatBytes(agent.dbBytes)}</td>
                    <td className="py-3 pr-4">{formatBytes(agent.storageBytes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  )
}
