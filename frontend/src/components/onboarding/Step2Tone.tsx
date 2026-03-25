"use client"
import { useState } from "react"
import { cn } from "@/utils/cn"

const TONES = [
  { id: "official", label: "공식적/신뢰감", desc: "기관·기업 공식 계정 느낌" },
  { id: "casual", label: "친근/캐주얼", desc: "MZ세대 타깃, 편한 말투" },
  { id: "informative", label: "전문적/정보형", desc: "업계 지식 전달 중심" },
  { id: "emotional", label: "감성/스토리텔링", desc: "공감·감동 중심" },
  { id: "humor", label: "유머/위트", desc: "가볍고 재미있는 컨셉" },
  { id: "premium", label: "프리미엄/럭셔리", desc: "고급 브랜드 이미지" },
]

const EMOJI_OPTIONS = [
  { id: "full", label: "자주 사용" },
  { id: "minimal", label: "최소한만" },
  { id: "none", label: "사용 안함" },
]

const HASHTAG_OPTIONS = [
  { id: "full", label: "많이 (30개)" },
  { id: "medium", label: "적당히 (5~10개)" },
  { id: "minimal", label: "최소 (3개 이하)" },
  { id: "none", label: "미사용" },
]

interface Props {
  onNext: (data: object) => void
  loading: boolean
}

export default function Step2Tone({ onNext, loading }: Props) {
  const [tones, setTones] = useState<string[]>([])
  const [forbidden, setForbidden] = useState("")
  const [emoji, setEmoji] = useState("minimal")
  const [hashtag, setHashtag] = useState("medium")
  const [notes, setNotes] = useState("")

  function toggleTone(id: string) {
    setTones(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id])
  }

  function handleNext() {
    onNext({
      tones,
      forbidden_words: forbidden.split(",").map(w => w.trim()).filter(Boolean),
      emoji_policy: emoji,
      hashtag_policy: hashtag,
      extra_notes: notes || null,
    })
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-2">톤앤매너를 설정해주세요</h2>
      <p className="text-gray-500 text-sm mb-6">복수 선택 가능합니다</p>

      <div className="mb-6">
        <label className="block text-sm font-medium mb-3">기본 톤 선택</label>
        <div className="grid grid-cols-2 gap-2">
          {TONES.map(({ id, label, desc }) => (
            <button
              key={id}
              onClick={() => toggleTone(id)}
              className={cn(
                "text-left p-3 rounded-xl border text-sm transition-all",
                tones.includes(id)
                  ? "border-blue-500 bg-blue-50 text-blue-700"
                  : "border-gray-200 hover:border-gray-300 text-gray-700"
              )}
            >
              <p className="font-medium">{label}</p>
              <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">금지 표현 (쉼표로 구분)</label>
        <input
          value={forbidden}
          onChange={e => setForbidden(e.target.value)}
          placeholder="예: 경쟁사명, 특정단어"
          className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium mb-2">이모지 사용</label>
          <div className="flex gap-2">
            {EMOJI_OPTIONS.map(({ id, label }) => (
              <button key={id} onClick={() => setEmoji(id)}
                className={cn("flex-1 py-2 text-xs rounded-lg border transition-all",
                  emoji === id ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-600")}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">해시태그 전략</label>
          <div className="flex gap-1">
            {HASHTAG_OPTIONS.map(({ id, label }) => (
              <button key={id} onClick={() => setHashtag(id)}
                className={cn("flex-1 py-2 text-xs rounded-lg border transition-all",
                  hashtag === id ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-600")}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mb-8">
        <label className="block text-sm font-medium mb-2">추가 메모 (선택)</label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={2}
          placeholder="특별히 전달하고 싶은 내용..."
          className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      </div>

      <button
        onClick={handleNext}
        disabled={tones.length === 0 || loading}
        className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {loading ? "저장 중..." : "다음 →"}
      </button>
    </div>
  )
}
