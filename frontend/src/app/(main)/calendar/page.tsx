"use client"
import { useEffect, useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import api from "@/services/api"
import { useRouter } from "next/navigation"
import { useSelectedClient } from "@/hooks/useSelectedClient"

interface ScheduleItem {
  id: string
  content_id: string
  title: string
  scheduled_at: string
  platform: string
  status: string
  account_name?: string | null
  token_expires_at?: string | null
  channel_health?: "healthy" | "expiring" | "reauth_required" | "unknown"
}

export default function CalendarPage() {
  const router = useRouter()
  const { selectedClientId, selectedClient, loading: clientLoading } = useSelectedClient()
  const [currentDate, setCurrentDate] = useState(new Date())
  const [schedules, setSchedules] = useState<ScheduleItem[]>([])
  const [loading, setLoading] = useState(true)

  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  useEffect(() => {
    if (clientLoading || !selectedClientId) return

    void Promise.resolve().then(() => {
      const start = new Date(year, month, 1).toISOString()
      const end = new Date(year, month + 1, 0, 23, 59, 59).toISOString()
      setLoading(true)
      return api.get(`/api/v1/schedule/calendar?client_id=${selectedClientId}&start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`)
        .then((r) => {
          const items = r.data?.items || []
          setSchedules(Array.isArray(items) ? items : [])
        })
        .catch(() => setSchedules([]))
        .finally(() => setLoading(false))
    })
  }, [year, month, selectedClientId, clientLoading])

  const visibleSchedules = selectedClientId ? schedules : []

  const healthBadgeClass = (health?: ScheduleItem["channel_health"]) => {
    if (health === "healthy") return "bg-blue-100 text-blue-700"
    if (health === "expiring") return "bg-yellow-100 text-yellow-700"
    if (health === "reauth_required") return "bg-red-100 text-red-700"
    return "bg-gray-100 text-gray-600"
  }

  const healthLabel = (health?: ScheduleItem["channel_health"]) => {
    if (health === "healthy") return "정상"
    if (health === "expiring") return "임박"
    if (health === "reauth_required") return "재인증"
    return "미확인"
  }

  const getItemsForDay = (day: number) => {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`
    return visibleSchedules.filter((s) => s.scheduled_at?.startsWith(dateStr))
  }

  const today = new Date()
  const isToday = (day: number) => today.getFullYear() === year && today.getMonth() === month && today.getDate() === day

  const days = ["일", "월", "화", "수", "목", "금", "토"]
  const cells = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">캘린더</h1>
          {selectedClient && <p className="text-sm text-gray-500 mt-1">{selectedClient.name}</p>}
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setCurrentDate(new Date(year, month - 1))} className="p-2 hover:bg-gray-100 rounded"><ChevronLeft size={20} /></button>
          <span className="text-lg font-semibold">{year}년 {month + 1}월</span>
          <button onClick={() => setCurrentDate(new Date(year, month + 1))} className="p-2 hover:bg-gray-100 rounded"><ChevronRight size={20} /></button>
        </div>
      </div>
      {!selectedClientId && !loading ? (
        <div className="bg-white border rounded-lg p-6 text-sm text-gray-500">선택된 클라이언트가 없습니다.</div>
      ) : (
        <>
          <div className="grid grid-cols-7 border rounded-lg overflow-hidden bg-white">
            {days.map((d) => <div key={d} className="p-2 text-center text-xs font-medium text-gray-500 bg-gray-50 border-b">{d}</div>)}
            {cells.map((day, i) => (
              <div key={i} className={`min-h-[100px] p-1 border-b border-r ${day && isToday(day) ? "bg-blue-50" : "bg-white"}`}>
                {day && (
                  <>
                    <span className={`text-xs ${isToday(day) ? "bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center" : "text-gray-600"}`}>{day}</span>
                    {getItemsForDay(day).map((item) => (
                      <div
                        key={item.id}
                        onClick={() => router.push(`/contents/${item.content_id}`)}
                        className="mt-1 px-1.5 py-1 text-xs border rounded cursor-pointer hover:bg-gray-50"
                        title={`${item.title} · ${item.platform}${item.account_name ? ` · ${item.account_name}` : ""}`}
                      >
                        <div className="font-medium text-gray-700 truncate">{item.title || "예약 콘텐츠"}</div>
                        <div className="flex items-center justify-between gap-1 mt-1">
                          <span className="text-[10px] text-gray-500 truncate">{item.platform}</span>
                          <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${healthBadgeClass(item.channel_health)}`}>
                            {healthLabel(item.channel_health)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            ))}
          </div>
          {loading && <p className="text-center text-gray-400 mt-4">로딩 중...</p>}
        </>
      )}
    </div>
  )
}
