"use client"
import { useState } from "react"
import { cn } from "@/utils/cn"

const CHANNELS = [
  { id: "instagram", label: "인스타그램", emoji: "📸", desc: "피드/릴스/스토리" },
  { id: "facebook", label: "페이스북", emoji: "👥", desc: "페이지/광고 연동" },
  { id: "x", label: "X (트위터)", emoji: "✖️", desc: "트윗/스레드/DM" },
  { id: "threads", label: "Threads", emoji: "🧵", desc: "Meta 계열" },
  { id: "kakao", label: "카카오채널", emoji: "💬", desc: "알림톡/챗봇" },
  { id: "tiktok", label: "틱톡", emoji: "🎵", desc: "숏폼 영상" },
  { id: "linkedin", label: "링크드인", emoji: "💼", desc: "B2B 마케팅" },
  { id: "youtube", label: "유튜브", emoji: "▶️", desc: "쇼츠/롱폼 영상" },
]

interface Props {
  onNext: (channels: string[]) => void
  loading: boolean
}

export default function Step3Channels({ onNext, loading }: Props) {
  const [selected, setSelected] = useState<string[]>(["instagram", "facebook"])

  function toggle(id: string) {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    )
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-2">운영할 채널을 선택해주세요</h2>
      <p className="text-gray-500 text-sm mb-6">복수 선택 가능합니다. 나중에 변경할 수 있어요</p>

      <div className="grid grid-cols-2 gap-3 mb-8">
        {CHANNELS.map(({ id, label, emoji, desc }) => (
          <button
            key={id}
            onClick={() => toggle(id)}
            className={cn(
              "flex items-center gap-3 p-4 rounded-xl border text-left transition-all",
              selected.includes(id)
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300"
            )}
          >
            <span className="text-2xl">{emoji}</span>
            <div>
              <p className={cn("text-sm font-medium",
                selected.includes(id) ? "text-blue-700" : "text-gray-700")}>
                {label}
              </p>
              <p className="text-xs text-gray-400">{desc}</p>
            </div>
            {selected.includes(id) && (
              <span className="ml-auto text-blue-600 text-xs font-bold">✓</span>
            )}
          </button>
        ))}
      </div>

      <p className="text-sm text-gray-500 mb-4">
        선택된 채널: <span className="font-medium text-blue-600">{selected.length}개</span>
      </p>

      <button
        onClick={() => onNext(selected)}
        disabled={selected.length === 0 || loading}
        className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {loading ? "저장 중..." : "다음 →"}
      </button>
    </div>
  )
}
