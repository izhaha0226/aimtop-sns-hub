"use client"
import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const router = useRouter()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await login(email, password)
      router.push("/dashboard")
    } catch {
      setError("이메일 또는 비밀번호가 올바르지 않습니다")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow-sm border w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-1">AimTop SNS Hub</h1>
        <p className="text-gray-500 text-sm mb-6">SNS 자동화 플랫폼</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">이메일</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="admin@aimtop.ai"
              required
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium">비밀번호</label>
              <Link href="/forgot-password" className="text-xs text-blue-600 hover:underline">비밀번호 찾기</Link>
            </div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "로그인 중..." : "로그인"}
          </button>
        </form>
        <div className="mt-5 text-sm text-gray-500">
          초대 링크가 있으신가요? <Link href="/signup" className="text-blue-600 hover:underline">초대 수락</Link>
        </div>
        <div className="mt-6 border-t pt-4 text-center text-xs text-gray-500">
          <p className="mb-2">로그인 없이 확인 가능한 공개 문서</p>
          <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-2">
            <Link href="/privacy" className="text-blue-600 hover:underline">개인정보처리방침</Link>
            <span className="text-gray-300">|</span>
            <Link href="/terms" className="text-blue-600 hover:underline">서비스 이용약관</Link>
            <span className="text-gray-300">|</span>
            <Link href="/data-deletion" className="text-blue-600 hover:underline">사용자 데이터 삭제</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
