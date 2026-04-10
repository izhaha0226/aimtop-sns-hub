"use client"

import { Suspense, useMemo, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { authService } from "@/services/auth"

function SignupInviteContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const inviteToken = useMemo(() => searchParams.get("invite") || "", [searchParams])

  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!inviteToken) {
      setError("유효한 초대 토큰이 없습니다")
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
    try {
      await authService.acceptInvite(inviteToken, password)
      router.push("/dashboard")
    } catch {
      setError("초대 수락에 실패했습니다")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white p-8 rounded-xl shadow-sm border w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-1">초대 수락</h1>
        <p className="text-gray-500 text-sm mb-6">초대받은 계정의 비밀번호를 설정해 주세요.</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">비밀번호</label>
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
          {!inviteToken && <p className="text-amber-600 text-sm">초대 링크에 토큰이 없습니다.</p>}
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading || !inviteToken}
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "처리 중..." : "초대 수락"}
          </button>
        </form>
        <div className="mt-5 text-sm text-gray-500">
          <Link href="/login" className="text-blue-600 hover:underline">로그인으로 이동</Link>
        </div>
      </div>
    </div>
  )
}

export default function SignupInvitePage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-500">불러오는 중...</div>}>
      <SignupInviteContent />
    </Suspense>
  )
}
