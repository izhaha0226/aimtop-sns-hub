"use client"

import { useRouter } from "next/navigation"
import { ArrowLeft, ImagePlus, FileText, LayoutTemplate, Sparkles, Share2 } from "lucide-react"

const OPTIONS = [
  {
    title: "주제 기반 멀티채널 카드뉴스",
    description: "한 가지 주제로 5장 카드뉴스 내용부터 만들고, 첫 장 3시안 선택 후 채널별 콘텐츠로 저장합니다.",
    href: "/contents/new/topic",
    icon: Share2,
    points: ["5장 스토리라인 먼저 생성", "실사1/실사2/일러스트 첫 장 시안", "Instagram/Facebook/Threads 등 변환"],
  },
  {
    title: "텍스트 콘텐츠",
    description: "벤치마킹 계정 참고 + 본문 작성 + 이미지 첨부까지 바로 진행합니다.",
    href: "/contents/new/text",
    icon: FileText,
    points: ["벤치마킹 채널 메모", "텍스트 훅/CTA 작성", "이미지 드래그 삽입"],
  },
  {
    title: "카드뉴스",
    description: "카드 흐름 기획, 벤치마킹, 레퍼런스 이미지 드래그 삽입 중심 화면입니다.",
    href: "/contents/new/card-news",
    icon: LayoutTemplate,
    points: ["벤치마킹 채널 등록", "슬라이드 구조 메모", "시안 이미지 업로드/드래그"],
  },
]

export default function ContentNewPage() {
  const router = useRouter()

  return (
    <div className="max-w-4xl">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => router.back()} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-xl font-bold">새 콘텐츠</h1>
          <p className="text-sm text-gray-500 mt-1">원래 쓰시던 벤치마킹/이미지 삽입 흐름 기준으로 작성 타입을 먼저 선택합니다.</p>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-5">
        {OPTIONS.map((option) => {
          const Icon = option.icon
          return (
            <button
              key={option.href}
              type="button"
              onClick={() => router.push(option.href)}
              className="text-left bg-white rounded-2xl border p-6 hover:border-blue-400 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-medium mb-3">
                    <Sparkles size={12} />
                    추천 작성 흐름
                  </div>
                  <h2 className="text-lg font-semibold text-gray-900">{option.title}</h2>
                  <p className="text-sm text-gray-500 mt-2 leading-6">{option.description}</p>
                </div>
                <div className="w-11 h-11 rounded-xl bg-gray-50 border flex items-center justify-center text-blue-600">
                  <Icon size={20} />
                </div>
              </div>

              <div className="space-y-2">
                {option.points.map((point) => (
                  <div key={point} className="flex items-center gap-2 text-sm text-gray-700">
                    <ImagePlus size={14} className="text-gray-400" />
                    {point}
                  </div>
                ))}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
