"use client"

import { useState } from "react"
import Link from "next/link"
import { authService } from "@/services/auth"

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError("")
    setMessage("")
    try {
      const res = await authService.forgotPassword(email)
      setMessage(res?.message || "재설정 링크를 발송했습니다")
    } catch {
      setError("재설정 메일 발송에 실패했습니다")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white p-8 rounded-xl shadow-sm border w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-1">비밀번호 재설정</h1>
        <p className="text-gray-500 text-sm mb-6">가입한 이메일로 재설정 링크를 발송합니다.</p>
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
          {message && <p className="text-green-600 text-sm">{message}</p>}
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "발송 중..." : "재설정 링크 보내기"}
          </button>
        </form>
        <div className="mt-5 text-sm text-gray-500">
          <Link href="/login" className="text-blue-600 hover:underline">로그인으로 돌아가기</Link>
        </div>
      </div>
    </div>
  )
}
