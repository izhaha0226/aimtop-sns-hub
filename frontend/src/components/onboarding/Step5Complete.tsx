"use client"
import { useEffect, useState } from "react"
import { CheckCircle2, FileText } from "lucide-react"
import { onboardingService } from "@/services/onboarding"

interface Props {
  clientId: string
  onDone: () => void
}

export default function Step5Complete({ clientId, onDone }: Props) {
  const [strategy, setStrategy] = useState("")

  useEffect(() => {
    onboardingService.get(clientId).then(data => {
      setStrategy(data.strategy_content || "")
    })
  }, [clientId])

  return (
    <div className="text-center">
      <div className="flex justify-center mb-4">
        <CheckCircle2 size={48} className="text-green-500" />
      </div>
      <h2 className="text-xl font-bold mb-2">온보딩 완료!</h2>
      <p className="text-gray-500 text-sm mb-6">
        AI가 채널 운영 전략서를 생성했습니다
      </p>

      {strategy && (
        <div className="text-left bg-gray-50 rounded-xl p-4 mb-6 max-h-64 overflow-y-auto">
          <div className="flex items-center gap-2 mb-3">
            <FileText size={16} className="text-blue-600" />
            <span className="text-sm font-medium text-blue-600">채널 운영 전략서</span>
          </div>
          <pre className="text-xs text-gray-600 whitespace-pre-wrap font-sans">{strategy}</pre>
        </div>
      )}

      <button
        onClick={onDone}
        className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 transition-colors"
      >
        대시보드로 이동 →
      </button>
    </div>
  )
}
