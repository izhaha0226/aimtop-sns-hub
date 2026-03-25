"use client"
import { useEffect, useState } from "react"
import { Plus, Building2 } from "lucide-react"
import { clientsService } from "@/services/clients"

interface Client {
  id: string
  name: string
  account_type: string
  brand_color: string | null
  created_at: string
}

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    clientsService.list()
      .then(setClients)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">클라이언트</h1>
        <button className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors">
          <Plus size={16} />
          클라이언트 추가
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
            <div key={c.id} className="bg-white rounded-xl border p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-center gap-3 mb-2">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold"
                  style={{ backgroundColor: c.brand_color || "#3B82F6" }}
                >
                  {c.name[0]}
                </div>
                <h3 className="font-medium text-sm">{c.name}</h3>
              </div>
              <p className="text-xs text-gray-400">{c.account_type}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
