"use client"
import { Bell, ChevronDown, CheckCheck, LogOut, User } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { useParams, usePathname, useRouter } from "next/navigation"
import { useSelectedClient } from "@/hooks/useSelectedClient"
import { notificationsService, type NotificationItem } from "@/services/notifications"

export default function Header() {
  const { user, logout } = useAuth()
  const params = useParams<{ id?: string | string[] }>()
  const pathname = usePathname()
  const { clients, selectedClientId, selectClient } = useSelectedClient()
  const [profileOpen, setProfileOpen] = useState(false)
  const [clientOpen, setClientOpen] = useState(false)
  const [notificationOpen, setNotificationOpen] = useState(false)
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const router = useRouter()
  const notificationRef = useRef<HTMLDivElement>(null)
  const profileRef = useRef<HTMLDivElement>(null)
  const clientRef = useRef<HTMLDivElement>(null)

  async function handleLogout() {
    await logout()
    router.push("/login")
  }

  async function loadNotifications() {
    try {
      const [items, count] = await Promise.all([
        notificationsService.list(10),
        notificationsService.unreadCount(),
      ])
      setNotifications(items)
      setUnreadCount(count)
    } catch {
      setNotifications([])
      setUnreadCount(0)
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadNotifications)
    const timer = window.setInterval(() => {
      void loadNotifications()
    }, 60000)
    return () => window.clearInterval(timer)
  }, [])

  const routeClientId = useMemo(() => {
    if (!pathname.startsWith("/clients/")) return ""
    if (!params?.id) return ""
    return Array.isArray(params.id) ? params.id[0] || "" : params.id
  }, [params, pathname])

  const activeClientId = routeClientId || selectedClientId
  const activeClientName = clients.find((client) => client.id === activeClientId)?.name || ""
  const hideClientSelector = Boolean(routeClientId)

  useEffect(() => {
    if (!routeClientId) return
    if (!clients.some((client) => client.id === routeClientId)) return
    if (selectedClientId === routeClientId) return
    selectClient(routeClientId)
  }, [clients, routeClientId, selectedClientId, selectClient])

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      const target = event.target as Node
      if (notificationRef.current && !notificationRef.current.contains(target)) setNotificationOpen(false)
      if (profileRef.current && !profileRef.current.contains(target)) setProfileOpen(false)
      if (clientRef.current && !clientRef.current.contains(target)) setClientOpen(false)
    }
    document.addEventListener("mousedown", handleOutsideClick)
    return () => document.removeEventListener("mousedown", handleOutsideClick)
  }, [])

  async function handleMarkAllRead() {
    try {
      await notificationsService.markAllRead()
      await loadNotifications()
    } catch {}
  }

  async function handleNotificationClick(item: NotificationItem) {
    try {
      if (!item.is_read) await notificationsService.markRead(item.id)
      await loadNotifications()
    } catch {}
    setNotificationOpen(false)
    if (item.link_url) router.push(item.link_url)
  }

  return (
    <header className="bg-white border-b px-6 py-3 flex items-center justify-between shrink-0">
      <div className="relative" ref={clientRef}>
        {!hideClientSelector && (
          <>
            <button
              onClick={() => setClientOpen((v) => !v)}
              className="flex items-center gap-2 text-sm font-medium border rounded-lg px-3 py-1.5 hover:bg-gray-50 min-w-[180px] justify-between"
            >
              <span className="truncate">{activeClientName || "클라이언트 선택"}</span>
              <ChevronDown size={14} />
            </button>
            {clientOpen && (
              <div className="absolute left-0 mt-1 w-64 bg-white border rounded-lg shadow-lg z-20 p-1">
                {clients.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-gray-400">클라이언트가 없습니다</div>
                ) : (
                  clients.map((client) => (
                    <button
                      key={client.id}
                      onClick={() => {
                        selectClient(client.id)
                        setClientOpen(false)
                      }}
                      className={`w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-gray-50 ${activeClientId === client.id ? "bg-blue-50 text-blue-700" : "text-gray-700"}`}
                    >
                      {client.name}
                    </button>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="relative" ref={notificationRef}>
          <button
            onClick={async () => {
              const nextOpen = !notificationOpen
              setNotificationOpen(nextOpen)
              if (nextOpen) await loadNotifications()
            }}
            className="relative p-2 hover:bg-gray-100 rounded-lg"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-5 h-5 px-1 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>
          {notificationOpen && (
            <div className="absolute right-0 mt-1 w-80 bg-white border rounded-lg shadow-lg z-20 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b">
                <span className="text-sm font-semibold">알림</span>
                <button onClick={handleMarkAllRead} className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
                  <CheckCheck size={12} /> 전체 읽음
                </button>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="px-4 py-6 text-sm text-gray-400 text-center">알림이 없습니다</div>
                ) : (
                  notifications.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleNotificationClick(item)}
                      className={`w-full text-left px-4 py-3 border-b last:border-b-0 hover:bg-gray-50 ${item.is_read ? "bg-white" : "bg-blue-50/50"}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{item.title}</p>
                          {item.message && <p className="text-xs text-gray-500 mt-1 whitespace-pre-wrap">{item.message}</p>}
                        </div>
                        {!item.is_read && <span className="w-2 h-2 rounded-full bg-blue-600 mt-1.5 shrink-0" />}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            className="flex items-center gap-2 text-sm hover:bg-gray-50 px-3 py-1.5 rounded-lg"
          >
            <User size={16} />
            {user?.name}
            <ChevronDown size={14} />
          </button>
          {profileOpen && (
            <div className="absolute right-0 mt-1 w-40 bg-white border rounded-lg shadow-lg z-20">
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-gray-50 rounded-lg"
              >
                <LogOut size={14} />
                로그아웃
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
