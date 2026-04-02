"use client"
import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { Plus, Building2, Pencil, Trash2, X } from "lucide-react"
import { clientsService } from "@/services/clients"

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

const emptyForm: FormData = {
  name: "",
  industry_category: "",
  brand_color: "#3B82F6",
  logo: "",
  account_type: "brand",
}

export default function ClientsPage() {
  const router = useRouter()
  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<FormData>(emptyForm)
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(() => {
    clientsService.list()
      .then(setClients)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const openCreate = () => {
    setEditingId(null)
    setForm(emptyForm)
    setModalOpen(true)
  }

  const openEdit = (c: Client) => {
    setEditingId(c.id)
    setForm({
      name: c.name,
      industry_category: c.industry_category,
      brand_color: c.brand_color || "#3B82F6",
      logo: c.logo || "",
      account_type: c.account_type,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.industry_category) return
    setSubmitting(true)
    try {
      const payload = {
        name: form.name.trim(),
        industry_category: form.industry_category,
        brand_color: form.brand_color || null,
        logo: form.logo.trim() || null,
        account_type: form.account_type,
      }
      if (editingId) {
        await clientsService.update(editingId, payload)
      } else {
        await clientsService.create(payload as Parameters<typeof clientsService.create>[0])
      }
      setModalOpen(false)
      load()
    } catch (e) {
      console.error(e)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`"${name}" 클라이언트를 삭제하시겠습니까?`)) return
    try {
      await clientsService.delete(id)
      load()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">클라이언트 관리</h1>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} />
          새 클라이언트
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">불러오는 중...</div>
      ) : clients.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <Building2 size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400 text-sm">등록된 클라이언트가 없습니다</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {clients.map((c) => (
            <div
              key={c.id}
              className="group bg-white rounded-xl border p-4 hover:shadow-md transition-all cursor-pointer relative"
              onClick={() => router.push(`/clients/${c.id}`)}
            >
              <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={(e) => { e.stopPropagation(); openEdit(c) }}
                  className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-blue-600"
                >
                  <Pencil size={14} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(c.id, c.name) }}
                  className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-red-600"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              <div className="flex items-center gap-3 mb-3">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0"
                  style={{ backgroundColor: c.brand_color || "#3B82F6" }}
                >
                  {c.name[0]}
                </div>
                <div className="min-w-0">
                  <h3 className="font-medium text-sm truncate">{c.name}</h3>
                  <span className="inline-block mt-1 px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                    {c.industry_category}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>{c.account_type}</span>
                <span>{new Date(c.created_at).toLocaleDateString("ko-KR")}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setModalOpen(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold">{editingId ? "클라이언트 수정" : "새 클라이언트"}</h2>
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
                  placeholder="클라이언트 이름"
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
                {submitting ? "저장 중..." : editingId ? "수정" : "등록"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
