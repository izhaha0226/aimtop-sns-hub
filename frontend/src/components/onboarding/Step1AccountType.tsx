"use client"
import { useState } from "react"
import { Building2, ShoppingCart, Star, Briefcase, Calendar, MoreHorizontal } from "lucide-react"
import { cn } from "@/utils/cn"

const TYPES = [
  { id: "public", label: "공공기관 / 정부·지자체", icon: Building2, desc: "관공서, 공공기관 공식 계정" },
  { id: "product", label: "제품 중심 (커머스)", icon: ShoppingCart, desc: "온라인 쇼핑, 제품 판매" },
  { id: "brand", label: "브랜드 운영", icon: Star, desc: "브랜드 인지도, 팬덤 구축" },
  { id: "service", label: "서비스 홍보", icon: Briefcase, desc: "B2B/B2C 서비스 마케팅" },
  { id: "event", label: "이벤트·캠페인", icon: Calendar, desc: "특정 이벤트, 캠페인 전용" },
  { id: "etc", label: "기타", icon: MoreHorizontal, desc: "직접 설명" },
]

interface Props {
  onNext: (type: string) => void
  loading: boolean
}

export default function Step1AccountType({ onNext, loading }: Props) {
  const [selected, setSelected] = useState("")

  return (
    <div>
      <h2 className="text-xl font-bold mb-2">이 SNS 계정의 운영 목적은 무엇인가요?</h2>
      <p className="text-gray-500 text-sm mb-6">계정 유형에 따라 콘텐츠 전략과 톤앤매너 기본값이 달라집니다</p>
      <div className="grid grid-cols-2 gap-3 mb-8">
        {TYPES.map(({ id, label, icon: Icon, desc }) => (
          <button
            key={id}
            onClick={() => setSelected(id)}
            className={cn(
              "flex items-start gap-3 p-4 rounded-xl border text-left transition-all",
              selected === id
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300"
            )}
          >
            <Icon size={20} className={selected === id ? "text-blue-600" : "text-gray-400"} />
            <div>
              <p className={cn("text-sm font-medium", selected === id ? "text-blue-700" : "text-gray-700")}>
                {label}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
            </div>
          </button>
        ))}
      </div>
      <button
        onClick={() => selected && onNext(selected)}
        disabled={!selected || loading}
        className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {loading ? "저장 중..." : "다음 →"}
      </button>
    </div>
  )
}
