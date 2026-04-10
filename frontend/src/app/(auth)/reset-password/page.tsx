"use client"

import { Suspense, useMemo, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { authService } from "@/services/auth"

function ResetPasswordContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const token = useMemo(() => searchParams.get("token") || "", [searchParams])

  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!token) {
      setError("유효한 재설정 토큰이 없습니다")
      return
    }
    if (password.length < 8) {
      setError("비밀번호는 8자 이상이어야 합니다")
      return
    }
    if (password !== confirmPassword) {
      setError("비밀번호 확인이 일치하지 않습니다")
      return
    }

    setLoading(true)
    setError("")
    setMessage("")
    try {
      const res = await authService.resetPassword(token, password)
      setMessage(res?.message || "비밀번호가 변경되었습니다")
      setTimeout(() => router.push("/login"), 1200)
    } catch {
      setError("비밀번호 재설정에 실패했습니다")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white p-8 rounded-xl shadow-sm border w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-1">새 비밀번호 설정</h1>
        <p className="text-gray-500 text-sm mb-6">새 비밀번호를 입력해 주세요.</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">새 비밀번호</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">비밀번호 확인</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          {message && <p className="text-green-600 text-sm">{message}</p>}
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "변경 중..." : "비밀번호 변경"}
          </button>
        </form>
        <div className="mt-5 text-sm text-gray-500">
          <Link href="/login" className="text-blue-600 hover:underline">로그인으로 돌아가기</Link>
        </div>
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-500">불러오는 중...</div>}>
      <ResetPasswordContent />
    </Suspense>
  )
}
