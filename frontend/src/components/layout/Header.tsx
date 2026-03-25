"use client"
import { Bell, ChevronDown, LogOut, User } from "lucide-react"
import { useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"

export default function Header() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const router = useRouter()

  async function handleLogout() {
    await logout()
    router.push("/login")
  }

  return (
    <header className="bg-white border-b px-6 py-3 flex items-center justify-between shrink-0">
      <button className="flex items-center gap-2 text-sm font-medium border rounded-lg px-3 py-1.5 hover:bg-gray-50">
        클라이언트 선택
        <ChevronDown size={14} />
      </button>
      <div className="flex items-center gap-3">
        <button className="p-2 hover:bg-gray-100 rounded-lg">
          <Bell size={18} />
        </button>
        <div className="relative">
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center gap-2 text-sm hover:bg-gray-50 px-3 py-1.5 rounded-lg"
          >
            <User size={16} />
            {user?.name}
            <ChevronDown size={14} />
          </button>
          {open && (
            <div className="absolute right-0 mt-1 w-40 bg-white border rounded-lg shadow-lg z-10">
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
