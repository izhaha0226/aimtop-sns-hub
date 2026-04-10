import fs from "fs"
import os from "os"
import path from "path"
import { execSync } from "child_process"

type AgentKey = string

type AgentKind = "hermes" | "openclaw" | "claude"

type AgentMetric = {
  key: AgentKey
  name: string
  runtime: string
  modelLabel: string
  modelDetail: string
  homePath: string
  status: "running" | "stopped"
  processCount: number
  pidText: string
  cpuPercent: number
  rssBytes: number
  ramSharePercent: number
  cacheBytes: number
  uptimeSeconds: number
  storageBytes: number
  sessionBytes: number
  logBytes: number
  dbBytes: number
  sessionCount: number
  cronCount: number
  delegateTraceCount: number
  gatewayErrors: number
  latestActivity: string | null
  gatewayState: string
  contextSummary: string
  memorySummary: string
  notes: string[]
}

type FleetMetric = {
  generatedAt: string
  agents: AgentMetric[]
  activeAgents: number
  totalRssBytes: number
  totalStorageBytes: number
  systemRamBytes: number
  liveGateways: number
  tunnelProcesses: number
  warnings: string[]
}

type ProcessRow = {
  pid: number
  cpuPercent: number
  rssBytes: number
  uptimeSeconds: number
  command: string
}

type AgentDescriptor = {
  key: AgentKey
  kind: AgentKind
  name: string
  runtime: string
  homePath: string
  configPath: string
  sessionDir: string
  logFiles: readonly string[]
  gatewayHint: string
}

function safeRead(filePath: string) {
  try {
    return fs.readFileSync(filePath, "utf-8")
  } catch {
    return ""
  }
}

function safeStat(filePath: string) {
  try {
    return fs.statSync(filePath)
  } catch {
    return null
  }
}

function exists(filePath: string) {
  return Boolean(safeStat(filePath))
}

function walkSize(targetPath: string): number {
  try {
    const stat = fs.statSync(targetPath)
    if (stat.isFile()) return stat.size
    if (!stat.isDirectory()) return 0
    let total = 0
    for (const entry of fs.readdirSync(targetPath)) total += walkSize(path.join(targetPath, entry))
    return total
  } catch {
    return 0
  }
}

function listFiles(targetPath: string): string[] {
  try {
    return fs.readdirSync(targetPath).map((name) => path.join(targetPath, name))
  } catch {
    return []
  }
}

function getSystemRamBytes() {
  return os.totalmem()
}

function cacheFootprint(homePath: string) {
  const candidates = [
    path.join(homePath, "cache"),
    path.join(homePath, ".cache"),
    path.join(homePath, "Library", "Caches"),
  ]
  return candidates.reduce((sum, targetPath) => sum + walkSize(targetPath), 0)
}

function latestMtimeMs(targets: readonly string[]): number {
  let best = 0
  for (const target of targets) {
    const stat = safeStat(target)
    if (stat && stat.mtimeMs > best) best = stat.mtimeMs
  }
  return best
}

function parseElapsed(raw: string): number {
  const text = raw.trim()
  if (!text) return 0
  let days = 0
  let clock = text
  if (text.includes("-")) {
    const parts = text.split("-")
    days = Number(parts[0]) || 0
    clock = parts[1]
  }
  const nums = clock.split(":").map((v) => Number(v) || 0)
  if (nums.length === 3) return days * 86400 + nums[0] * 3600 + nums[1] * 60 + nums[2]
  if (nums.length === 2) return days * 86400 + nums[0] * 60 + nums[1]
  return days * 86400
}

function parseProcesses(): ProcessRow[] {
  const out = execSync("ps eww -axo pid=,pcpu=,rss=,etime=,args=", { encoding: "utf-8" })
  return out
    .split(/\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const match = line.match(/^(\d+)\s+([\d.]+)\s+(\d+)\s+(\S+)\s+(.*)$/)
      if (!match) return null
      const [, pid, cpu, rssKb, etime, command] = match
      return {
        pid: Number(pid),
        cpuPercent: Number(cpu),
        rssBytes: Number(rssKb) * 1024,
        uptimeSeconds: parseElapsed(etime),
        command,
      }
    })
    .filter((row): row is ProcessRow => Boolean(row))
}

function tailText(filePath: string, maxChars = 12000) {
  return safeRead(filePath).slice(-maxChars)
}

function countMatches(text: string, pattern: RegExp) {
  return (text.match(pattern) || []).length
}

function formatBytes(bytes: number) {
  if (!bytes) return "0 B"
  const units = ["B", "KB", "MB", "GB", "TB"]
  let value = bytes
  let idx = 0
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024
    idx += 1
  }
  return `${value >= 100 ? value.toFixed(0) : value.toFixed(1)} ${units[idx]}`
}

function formatDuration(seconds: number) {
  if (!seconds) return "0m"
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d) return `${d}d ${h}h`
  if (h) return `${h}h ${m}m`
  return `${m}m`
}

function countSessionFiles(sessionDir: string) {
  return listFiles(sessionDir).filter((filePath) => safeStat(filePath)?.isFile()).length
}

function countCronFiles(sessionDir: string) {
  return listFiles(sessionDir).filter((filePath) => path.basename(filePath).includes("cron")).length
}

function countDelegateTraces(sessionDir: string) {
  const files = listFiles(sessionDir)
    .filter((filePath) => safeStat(filePath)?.isFile())
    .sort((a, b) => (safeStat(b)?.mtimeMs || 0) - (safeStat(a)?.mtimeMs || 0))
    .slice(0, 25)
  let total = 0
  for (const filePath of files) total += countMatches(tailText(filePath, 20000), /delegate_task|subagent|delegateTask/gi)
  return total
}

function countGatewayErrors(logFiles: readonly string[]) {
  return logFiles.reduce((sum, filePath) => sum + countMatches(tailText(filePath), /\bERROR\b|\bERR\b|Traceback|Unhandled|Exception/gi), 0)
}

function gatewayStateFromLogs(logFiles: readonly string[], isRunning: boolean, hint: string) {
  const combined = logFiles.map((filePath) => tailText(filePath, 8000)).join("\n")
  if (/Connected to Telegram|Gateway running with|Connected and polling|Connected to Telegram \(polling mode\)/i.test(combined)) {
    return isRunning ? `연결됨 (${hint})` : `로그상 연결됨 (${hint})`
  }
  if (/Connection terminated|Unable to reach the origin|Invalid API key|ReadTimeout|error/i.test(combined)) {
    return `주의 (${hint})`
  }
  return isRunning ? `실행중 (${hint})` : `중지 (${hint})`
}

function parseHermesModel(configText: string) {
  const defaultModel = /default:\s+(.+)/.exec(configText)?.[1]?.trim() ?? "-"
  const provider = /provider:\s+(.+)/.exec(configText)?.[1]?.trim() ?? "-"
  const baseUrl = /base_url:\s+(.+)/.exec(configText)?.[1]?.trim() ?? ""
  const compact = /summary_model:\s+(.+)/.exec(configText)?.[1]?.trim() ?? "-"
  return {
    modelLabel: `${defaultModel} (${provider})`,
    modelDetail: baseUrl ? `base_url ${baseUrl} · summary ${compact}` : `summary ${compact}`,
  }
}

function parseOpenClawModel(configText: string) {
  try {
    const parsed = JSON.parse(configText)
    const primary = parsed?.agents?.defaults?.model?.primary || "-"
    const fallback = Array.isArray(parsed?.agents?.defaults?.model?.fallbacks) ? parsed.agents.defaults.model.fallbacks.join(", ") : "-"
    return {
      modelLabel: String(primary),
      modelDetail: `fallback ${fallback}`,
    }
  } catch {
    return { modelLabel: "설정 파싱 실패", modelDetail: "-" }
  }
}

function claudeModelInfo() {
  return {
    modelLabel: "Claude CLI",
    modelDetail: "로컬 인증 기반 CLI 세션",
  }
}

function hermesContextSummary(configText: string) {
  const compressionEnabled = /compression:\n(?:.*\n){0,8}?\s+enabled:\s+(true|false)/m.exec(configText)?.[1] ?? "unknown"
  const threshold = /compression:\n(?:.*\n){0,8}?\s+threshold:\s+([\d.]+)/m.exec(configText)?.[1] ?? "-"
  const targetRatio = /compression:\n(?:.*\n){0,8}?\s+target_ratio:\s+([\d.]+)/m.exec(configText)?.[1] ?? "-"
  return `압축 ${compressionEnabled} · threshold ${threshold} · target ${targetRatio}`
}

function hermesMemorySummary(configText: string) {
  const memoryEnabled = /memory_enabled:\s+(true|false)/.exec(configText)?.[1] ?? "unknown"
  const memoryLimit = /memory_char_limit:\s+(\d+)/.exec(configText)?.[1] ?? "-"
  const userLimit = /user_char_limit:\s+(\d+)/.exec(configText)?.[1] ?? "-"
  const provider = /memory:\n(?:.*\n){0,8}?\s+provider:\s*(.*)/m.exec(configText)?.[1]?.trim() || "local"
  return `memory ${memoryEnabled} · memory ${memoryLimit}자 · user ${userLimit}자 · provider ${provider}`
}

function openclawContextSummary(configText: string) {
  try {
    const parsed = JSON.parse(configText)
    return `compaction ${parsed?.agents?.defaults?.compaction?.mode || "-"} · workspace ${parsed?.agents?.defaults?.workspace || "-"}`
  } catch {
    return "설정 파싱 실패"
  }
}

function openclawMemorySummary(configText: string) {
  try {
    const parsed = JSON.parse(configText)
    return `gateway ${parsed?.gateway?.mode || "-"}/${parsed?.gateway?.bind || "-"} · dmScope ${parsed?.session?.dmScope || "-"}`
  } catch {
    return "설정 파싱 실패"
  }
}

function isRecent(ms: number, minutes: number) {
  return ms > 0 && Date.now() - ms < minutes * 60 * 1000
}

function normalizeEnvPath(raw: string) {
  return raw.replace(/^['"]|['"]$/g, "")
}

function buildAgentKey(kind: AgentKind, targetPath: string) {
  const base = path.basename(targetPath).replace(/^\./, "") || kind
  const slug = `${kind}-${base}`.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")
  return slug || kind
}

function titleize(value: string) {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

function hermesDisplayName(homePath: string) {
  const base = path.basename(homePath)
  if (base === ".hermes") return "Hermes"
  return titleize(base.replace(/^\.hermes-?/, "Hermes ").replace(/^\./, ""))
}

function collectHermesHomes(processes: ProcessRow[], homeRoot: string) {
  const homes = new Set<string>()
  for (const filePath of listFiles(homeRoot)) {
    const stat = safeStat(filePath)
    if (!stat?.isDirectory()) continue
    const base = path.basename(filePath)
    if (!base.startsWith(".hermes")) continue
    if (exists(path.join(filePath, "config.yaml"))) homes.add(filePath)
  }
  for (const proc of processes) {
    if (!proc.command.includes("hermes gateway run")) continue
    const match = proc.command.match(/(?:^|\s)HERMES_HOME=([^\s]+)/)
    homes.add(match ? normalizeEnvPath(match[1]) : path.join(homeRoot, ".hermes"))
  }
  return Array.from(homes).sort()
}

function discoverAgents(processes: ProcessRow[]): AgentDescriptor[] {
  const homeRoot = process.env.HOME || "/Users/yosiki"
  const descriptors: AgentDescriptor[] = []

  for (const homePath of collectHermesHomes(processes, homeRoot)) {
    descriptors.push({
      key: buildAgentKey("hermes", homePath),
      kind: "hermes",
      name: hermesDisplayName(homePath),
      runtime: "Hermes",
      homePath,
      configPath: path.join(homePath, "config.yaml"),
      sessionDir: path.join(homePath, "sessions"),
      logFiles: [
        path.join(homePath, "logs", "gateway.log"),
        path.join(homePath, "logs", "gateway.error.log"),
        path.join(homePath, "logs", "agent.log"),
        path.join(homePath, "logs", "errors.log"),
      ],
      gatewayHint: "telegram",
    })
  }

  const openclawHome = path.join(homeRoot, ".openclaw")
  if (exists(path.join(openclawHome, "openclaw.json")) || processes.some((proc) => /(^|\s|\/)openclaw-gateway(\s|$)/.test(proc.command))) {
    descriptors.push({
      key: buildAgentKey("openclaw", openclawHome),
      kind: "openclaw",
      name: "OpenClaw",
      runtime: "OpenClaw",
      homePath: openclawHome,
      configPath: path.join(openclawHome, "openclaw.json"),
      sessionDir: path.join(openclawHome, "cron", "runs"),
      logFiles: [
        path.join(openclawHome, "logs", "gateway.log"),
        path.join(openclawHome, "logs", "gateway.err.log"),
        path.join(openclawHome, "logs", "commands.log"),
      ],
      gatewayHint: "telegram",
    })
  }

  const claudeHome = path.join(homeRoot, ".claude")
  if (exists(claudeHome) || processes.some((proc) => proc.command.trim() === "claude" || /(^|\s)claude(\s|$)/.test(proc.command))) {
    descriptors.push({
      key: buildAgentKey("claude", claudeHome),
      kind: "claude",
      name: "Claude CLI",
      runtime: "Claude CLI",
      homePath: claudeHome,
      configPath: "",
      sessionDir: path.join(claudeHome, "projects"),
      logFiles: [],
      gatewayHint: "local cli",
    })
  }

  return descriptors.sort((a, b) => a.name.localeCompare(b.name))
}

function processMatchesAgent(proc: ProcessRow, agent: AgentDescriptor, defaultHermesHome: string) {
  if (agent.kind === "hermes") {
    if (!proc.command.includes("hermes gateway run")) return false
    const match = proc.command.match(/(?:^|\s)HERMES_HOME=([^\s]+)/)
    const resolved = match ? normalizeEnvPath(match[1]) : defaultHermesHome
    return resolved === agent.homePath
  }
  if (agent.kind === "openclaw") return /(^|\s|\/)openclaw-gateway(\s|$)/.test(proc.command)
  return proc.command.trim() === "claude" || /(^|\s)claude(\s|$)/.test(proc.command)
}

function buildAgentMetric(agent: AgentDescriptor, processes: ProcessRow[], systemRamBytes: number): AgentMetric {
  const configText = agent.configPath ? safeRead(agent.configPath) : ""
  const defaultHermesHome = path.join(process.env.HOME || "/Users/yosiki", ".hermes")
  const matched = processes.filter((proc) => processMatchesAgent(proc, agent, defaultHermesHome))
  const latestActivityMs = latestMtimeMs([agent.homePath, agent.sessionDir, ...agent.logFiles])
  const recentLog = isRecent(latestActivityMs, 10)
  const status = matched.length > 0 || recentLog ? "running" : "stopped"
  const rssBytes = matched.reduce((sum, proc) => sum + proc.rssBytes, 0)
  const ramSharePercent = systemRamBytes > 0 ? (rssBytes / systemRamBytes) * 100 : 0
  const cacheBytes = cacheFootprint(agent.homePath)
  const cpuPercent = matched.reduce((sum, proc) => sum + proc.cpuPercent, 0)
  const uptimeSeconds = matched.reduce((max, proc) => Math.max(max, proc.uptimeSeconds), 0)
  const sessionCount = countSessionFiles(agent.sessionDir)
  const sessionBytes = walkSize(agent.sessionDir)
  const logBytes = agent.logFiles.reduce((sum, filePath) => sum + walkSize(filePath), 0)
  const dbBytes = agent.kind === "openclaw"
    ? walkSize(path.join(agent.homePath, "memory", "main.sqlite")) + walkSize(path.join(agent.homePath, "secrets.db"))
    : 0
  const storageBytes = walkSize(agent.homePath)
  const cronCount = agent.kind === "openclaw"
    ? (() => {
        try {
          const parsed = JSON.parse(safeRead(path.join(agent.homePath, "cron", "jobs.json")))
          return Array.isArray(parsed?.jobs) ? parsed.jobs.length : 0
        } catch {
          return 0
        }
      })()
    : countCronFiles(agent.sessionDir)
  const delegateTraceCount = agent.kind === "claude" ? 0 : countDelegateTraces(agent.sessionDir)
  const gatewayErrors = countGatewayErrors(agent.logFiles)
  const latestActivity = latestActivityMs ? new Date(latestActivityMs).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) : null

  const notes: string[] = []
  if (matched.length === 0 && recentLog) notes.push("프로세스 식별은 약하지만 로그 활동은 최근 기준 활성")
  if (matched.length === 0 && !recentLog) notes.push("현재 실행 프로세스 미탐지")
  if (gatewayErrors > 0) notes.push(`최근 에러 흔적 ${gatewayErrors}건`)
  if (agent.kind === "openclaw") notes.push("세션 대신 cron runs / memory DB 중심 관측")
  if (agent.kind === "claude") notes.push("CLI 프로세스/메모리만 직접 관측")
  if (agent.kind === "hermes" && /base_url http:\/\/(127\.0\.0\.1|localhost):\d+/m.test(configText)) notes.push("로컬 LLM 연동 구성 감지")

  const modelInfo = agent.kind === "openclaw"
    ? parseOpenClawModel(configText)
    : agent.kind === "claude"
      ? claudeModelInfo()
      : parseHermesModel(configText)

  const contextSummary = agent.kind === "openclaw"
    ? openclawContextSummary(configText)
    : agent.kind === "claude"
      ? "CLI 단독 실행 · 별도 compaction 정보 없음"
      : hermesContextSummary(configText)

  const memorySummary = agent.kind === "openclaw"
    ? openclawMemorySummary(configText)
    : agent.kind === "claude"
      ? "세션/메모리 설정 노출 없음"
      : hermesMemorySummary(configText)

  return {
    key: agent.key,
    name: agent.name,
    runtime: agent.runtime,
    modelLabel: modelInfo.modelLabel,
    modelDetail: modelInfo.modelDetail,
    homePath: agent.homePath,
    status,
    processCount: matched.length,
    pidText: matched.map((proc) => String(proc.pid)).join(", ") || "-",
    cpuPercent,
    rssBytes,
    ramSharePercent,
    cacheBytes,
    uptimeSeconds,
    storageBytes,
    sessionBytes,
    logBytes,
    dbBytes,
    sessionCount,
    cronCount,
    delegateTraceCount,
    gatewayErrors,
    latestActivity,
    gatewayState: gatewayStateFromLogs(agent.logFiles, status === "running", agent.gatewayHint),
    contextSummary,
    memorySummary,
    notes,
  }
}

export function collectFleetMetrics(): FleetMetric {
  const processes = parseProcesses()
  const systemRamBytes = getSystemRamBytes()
  const agents = discoverAgents(processes).map((agent) => buildAgentMetric(agent, processes, systemRamBytes))
  const activeAgents = agents.filter((agent) => agent.status === "running").length
  const totalRssBytes = agents.reduce((sum, agent) => sum + agent.rssBytes, 0)
  const totalStorageBytes = agents.reduce((sum, agent) => sum + agent.storageBytes, 0)
  const liveGateways = agents.filter((agent) => /연결됨|실행중|로그상 연결됨/.test(agent.gatewayState)).length
  const tunnelProcesses = processes.filter((proc) => proc.command.includes("cloudflared tunnel")).length
  const warnings: string[] = []

  const stopped = agents.filter((agent) => agent.status === "stopped").map((agent) => agent.name)
  if (stopped.length) warnings.push(`중지 상태 에이전트: ${stopped.join(", ")}`)
  if (tunnelProcesses > 1) warnings.push(`cloudflared 프로세스 ${tunnelProcesses}개 감지`)
  const noisy = agents.filter((agent) => agent.gatewayErrors > 0).map((agent) => `${agent.name}(${agent.gatewayErrors})`)
  if (noisy.length) warnings.push(`최근 오류 흔적: ${noisy.join(", ")}`)

  return {
    generatedAt: new Date().toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }),
    agents,
    activeAgents,
    totalRssBytes,
    totalStorageBytes,
    systemRamBytes,
    liveGateways,
    tunnelProcesses,
    warnings,
  }
}

export const agentMonitorFormatters = {
  formatBytes,
  formatDuration,
}
