"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard, Building2, FileText, Calendar,
  MessageSquare, BarChart3, TrendingUp, Settings
} from "lucide-react"
import { cn } from "@/utils/cn"

const menus = [
  { href: "/dashboard", icon: LayoutDashboard, label: "대시보드" },
  { href: "/clients", icon: Building2, label: "클라이언트" },
  { href: "/contents", icon: FileText, label: "콘텐츠" },
  { href: "/calendar", icon: Calendar, label: "캘린더" },
  { href: "/inbox", icon: MessageSquare, label: "인박스" },
  { href: "/analytics", icon: BarChart3, label: "분석" },
  { href: "/growth", icon: TrendingUp, label: "Growth Hub" },
  { href: "/settings/users", icon: Settings, label: "설정" },
]

export default function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="w-56 bg-white border-r flex flex-col shrink-0">
      <div className="p-4 border-b">
        <span className="font-bold text-blue-600 text-sm">AimTop SNS Hub</span>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {menus.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
              pathname.startsWith(href)
                ? "bg-blue-50 text-blue-700 font-medium"
                : "text-gray-600 hover:bg-gray-50"
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}
