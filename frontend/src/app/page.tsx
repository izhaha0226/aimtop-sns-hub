import type { Metadata } from "next"
import { headers } from "next/headers"
import { redirect } from "next/navigation"
import AgentMonitorPage from "./agent-monitor/page"

async function getHost() {
  const headerStore = await headers()
  return (headerStore.get("x-forwarded-host") || headerStore.get("host") || "").toLowerCase()
}

export async function generateMetadata(): Promise<Metadata> {
  const host = await getHost()

  if (host === "monitor.aimtop.ai") {
    return {
      title: "Agent Monitor | AimTop",
      description: "Hermes / Dev / Chief / Loke / Claude monitoring dashboard",
    }
  }

  return {
    title: "AimTop SNS Hub",
    description: "멀티 클라이언트 SNS 자동화 플랫폼",
  }
}

export default async function RootPage() {
  const host = await getHost()

  if (host === "monitor.aimtop.ai") {
    return <AgentMonitorPage />
  }

  redirect("/dashboard")
}
