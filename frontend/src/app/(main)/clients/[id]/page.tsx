"use client"
import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { clientsService } from "@/services/clients"
import { ArrowLeft } from "lucide-react"

interface Client {
  id: string
  name: string
  account_type: string
  brand_color: string | null
  logo: string | null
  created_at: string
}

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [client, setClient] = useState<Client | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    clientsService.get(id)
      .then(setClient)
      .catch(() => router.push("/clients"))
      .finally(() => setLoading(false))
  }, [id, router])

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
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center gap-4 mb-6">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-white text-lg font-bold"
            style={{ backgroundColor: client.brand_color || "#3B82F6" }}
          >
            {client.name[0]}
          </div>
          <div>
            <h1 className="text-xl font-bold">{client.name}</h1>
            <p className="text-sm text-gray-400">{client.account_type}</p>
          </div>
        </div>
        <div className="text-sm text-gray-500">
          등록일: {new Date(client.created_at).toLocaleDateString("ko-KR")}
        </div>
      </div>
    </div>
  )
}
