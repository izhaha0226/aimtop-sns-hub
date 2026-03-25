"use client"
import { useState } from "react"
import { Plus, X } from "lucide-react"

interface BenchmarkChannel {
  platform: string
  handle: string
  purpose: string
  memo: string
}

const PLATFORMS = ["instagram", "facebook", "x", "tiktok", "youtube", "linkedin", "threads"]

interface Props {
  onNext: (data: object[]) => void
  loading: boolean
}

export default function Step4Benchmark({ onNext, loading }: Props) {
  const [channels, setChannels] = useState<BenchmarkChannel[]>([
    { platform: "instagram", handle: "", purpose: "all", memo: "" }
  ])

  function addChannel() {
    if (channels.length >= 5) return
    setChannels(prev => [...prev, { platform: "instagram", handle: "", purpose: "all", memo: "" }])
  }

  function removeChannel(i: number) {
    setChannels(prev => prev.filter((_, idx) => idx !== i))
  }

  function updateChannel(i: number, field: keyof BenchmarkChannel, value: string) {
    setChannels(prev => prev.map((c, idx) => idx === i ? { ...c, [field]: value } : c))
  }

  const canProceed = channels.every(c => c.handle.trim())

  return (
    <div>
      <h2 className="text-xl font-bold mb-2">벤치마킹 채널을 등록해주세요</h2>
      <p className="text-gray-500 text-sm mb-6">
        참고할 SNS 계정을 입력하면 AI가 스타일을 분석해 전략에 반영합니다 (최대 5개)
      </p>

      <div className="space-y-4 mb-6">
        {channels.map((ch, i) => (
          <div key={i} className="border rounded-xl p-4 relative">
            {channels.length > 1 && (
              <button
                onClick={() => removeChannel(i)}
                className="absolute top-3 right-3 p-1 hover:bg-gray-100 rounded-lg"
              >
                <X size={14} />
              </button>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">플랫폼</label>
                <select
                  value={ch.platform}
                  onChange={e => updateChannel(i, "platform", e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {PLATFORMS.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">계정명 (@)</label>
                <input
                  value={ch.handle}
                  onChange={e => updateChannel(i, "handle", e.target.value)}
                  placeholder="@account_name"
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">벤치마킹 목적</label>
                <select
                  value={ch.purpose}
                  onChange={e => updateChannel(i, "purpose", e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">전체</option>
                  <option value="tone">톤앤매너</option>
                  <option value="format">콘텐츠 형식</option>
                  <option value="hashtag">해시태그</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">메모 (선택)</label>
                <input
                  value={ch.memo}
                  onChange={e => updateChannel(i, "memo", e.target.value)}
                  placeholder="이 채널처럼 운영하고 싶어요"
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {channels.length < 5 && (
        <button
          onClick={addChannel}
          className="w-full border-2 border-dashed border-gray-300 rounded-xl py-3 text-sm text-gray-400 hover:border-blue-400 hover:text-blue-500 flex items-center justify-center gap-2 mb-6 transition-colors"
        >
          <Plus size={16} />
          채널 추가 ({channels.length}/5)
        </button>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => onNext([])}
          className="flex-1 border border-gray-300 text-gray-600 py-3 rounded-xl text-sm hover:bg-gray-50 transition-colors"
        >
          건너뛰기
        </button>
        <button
          onClick={() => onNext(channels)}
          disabled={!canProceed || loading}
          className="flex-1 bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "분석 중..." : "완료 →"}
        </button>
      </div>
    </div>
  )
}
