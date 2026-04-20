"use client"
import Link from "next/link"
import { useEffect, useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { usersService } from "@/services/users"

interface User {
  id: string
  name: string
  email: string
  role: string
  status: string
}

const roleBadge: Record<string, string> = {
  admin: "bg-red-100 text-red-700",
  approver: "bg-purple-100 text-purple-700",
  editor: "bg-blue-100 text-blue-700",
  viewer: "bg-gray-100 text-gray-600",
}

const roleLabel: Record<string, string> = {
  admin: "Admin",
  approver: "Approver",
  editor: "Editor",
  viewer: "Viewer",
}

export default function UsersPage() {
  const { isAdmin, loading: authLoading } = useAuth()
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])

  useEffect(() => {
    if (!authLoading && !isAdmin) router.push("/dashboard")
  }, [isAdmin, authLoading, router])

  useEffect(() => {
    if (isAdmin) {
      usersService.list().then(setUsers).catch(console.error)
    }
  }, [isAdmin])

  if (authLoading) return null

  return (
    <div>
      <div className="flex gap-2 border-b pb-2 mb-6">
        <Link href="/settings/users" className="px-3 py-2 rounded-lg text-sm bg-blue-50 text-blue-700 font-medium">담당자 관리</Link>
        <Link href="/settings/secrets" className="px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50">시크릿 관리</Link>
        <Link href="/settings/ai-engine" className="px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50">AI 엔진 설정</Link>
      </div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">담당자 관리</h1>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors">
          + 담당자 초대
        </button>
      </div>
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              {["이름", "이메일", "역할", "상태", "관리"].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-gray-500 font-medium text-xs">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{u.name}</td>
                <td className="px-4 py-3 text-gray-500">{u.email}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${roleBadge[u.role]}`}>
                    {roleLabel[u.role]}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${
                    u.status === "active"
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-500"
                  }`}>
                    {u.status === "active" ? "활성" : "비활성"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button className="text-blue-600 hover:underline text-xs mr-3">수정</button>
                  <button className="text-red-500 hover:underline text-xs">비활성화</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
