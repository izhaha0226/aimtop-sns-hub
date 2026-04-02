"use client"
import { useEffect, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { clientsService } from "@/services/clients"
import { ArrowLeft, Pencil, Trash2, X, Link2 } from "lucide-react"

const INDUSTRY_CATEGORIES = [
  "식품/음료", "리테일/유통", "교육/학원", "부동산/건설",
  "금융/보험", "뷰티/패션", "IT/테크", "건강/의료",
  "여행/레저", "자동차", "콘텐츠/미디어", "공공/비영리",
  "제조업", "전문서비스", "기타",
]

interface Client {
  id: string
  name: string
  industry_category: string
  account_type: string
  brand_color: string | null
  logo: string | null
  created_at: string
}

interface FormData {
  name: string
  industry_category: string
  brand_color: string
  logo: string
  account_type: string
}

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [client, setClient] = useState<Client | null>(null)
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState<FormData>({ name: "", industry_category: "", brand_color: "#3B82F6", logo: "", account_type: "brand" })
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(() => {
    clientsService.get(id)
      .then(setClient)
      .catch(() => router.push("/clients"))
      .finally(() => setLoading(false))
  }, [id, router])

  useEffect(() => { load() }, [load])

  const openEdit = () => {
    if (!client) return
    setForm({
      name: client.name,
      industry_category: client.industry_category,
      brand_color: client.brand_color || "#3B82F6",
      logo: client.logo || "",
      account_type: client.account_type,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.industry_category) return
    setSubmitting(true)
    try {
      await clientsService.update(id, {
        name: form.name.trim(),
        industry_category: form.industry_category,
        brand_color: form.brand_color || null,
        logo: form.logo.trim() || null,
        account_type: form.account_type,
      })
      setModalOpen(false)
      load()
    } catch (e) {
      console.error(e)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!client) return
    if (!confirm(`"${client.name}" 클라이언트를 삭제하시겠습니까?\n삭제 후 복구할 수 없습니다.`)) return
    try {
      await clientsService.delete(id)
      router.push("/clients")
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-400">불러오는 중...</div>
  }

  if (!client) return null

  return (
    <div>
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft size={16} />
        뒤로
      </button>

      {/* Header Card */}
      <div className="bg-white rounded-xl border p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-xl flex items-center justify-center text-white text-xl font-bold"
              style={{ backgroundColor: client.brand_color || "#3B82F6" }}
            >
              {client.name[0]}
            </div>
            <div>
              <h1 className="text-xl font-bold">{client.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="inline-block px-2.5 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full font-medium">
                  {client.industry_category}
                </span>
                <span className="text-sm text-gray-400">{client.account_type}</span>
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={openEdit}
              className="flex items-center gap-2 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              <Pencil size={14} />
              수정
            </button>
            <button
              onClick={handleDelete}
              className="flex items-center gap-2 px-3 py-2 border border-red-200 rounded-lg text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              <Trash2 size={14} />
              삭제
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t">
          <div>
            <p className="text-xs text-gray-400 mb-1">브랜드 컬러</p>
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded" style={{ backgroundColor: client.brand_color || "#3B82F6" }} />
              <span className="text-sm">{client.brand_color || "#3B82F6"}</span>
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">계정 유형</p>
            <p className="text-sm">{client.account_type}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">등록일</p>
            <p className="text-sm">{new Date(client.created_at).toLocaleDateString("ko-KR")}</p>
          </div>
        </div>
      </div>

      {/* SNS Channels Section */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold">연결된 SNS 채널</h2>
        </div>
        <div className="text-center py-8">
          <Link2 size={28} className="mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">연결된 SNS 채널이 없습니다</p>
          <p className="text-xs text-gray-300 mt-1">설정에서 SNS 계정을 연동할 수 있습니다</p>
        </div>
      </div>

      {/* Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setModalOpen(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold">클라이언트 수정</h2>
              <button onClick={() => setModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">이름 *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">업종 카테고리 *</label>
                <select
                  value={form.industry_category}
                  onChange={(e) => setForm({ ...form, industry_category: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">선택하세요</option>
                  {INDUSTRY_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">브랜드 컬러</label>
                <div className="flex items-center gap-3">
                  <input
                    type="color"
                    value={form.brand_color}
                    onChange={(e) => setForm({ ...form, brand_color: e.target.value })}
                    className="w-10 h-10 rounded-lg border cursor-pointer"
                  />
                  <span className="text-sm text-gray-500">{form.brand_color}</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">로고 URL</label>
                <input
                  value={form.logo}
                  onChange={(e) => setForm({ ...form, logo: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="https://..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">계정 유형</label>
                <select
                  value={form.account_type}
                  onChange={(e) => setForm({ ...form, account_type: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="brand">브랜드</option>
                  <option value="agency">에이전시</option>
                  <option value="personal">개인</option>
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setModalOpen(false)}
                className="flex-1 border rounded-lg py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting || !form.name.trim() || !form.industry_category}
                className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {submitting ? "저장 중..." : "수정"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
