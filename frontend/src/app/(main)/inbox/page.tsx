"use client"
import { useEffect, useState } from "react"
import { MessageSquare, RefreshCw, EyeOff, Send } from "lucide-react"
import api from "@/services/api"

interface Comment {
  id: string
  author_name: string
  text: string
  sentiment: string | null
  created_at: string
  is_hidden: boolean
}

export default function InboxPage() {
  const [comments, setComments] = useState<Comment[]>([])
  const [loading, setLoading] = useState(true)
  const [replyText, setReplyText] = useState<Record<string, string>>({})
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    fetchComments()
  }, [])

  const fetchComments = () => {
    setLoading(true)
    api.get("/api/v1/comments/all?limit=50")
      .then(r => setComments(r.data?.items || r.data || []))
      .catch(() => setComments([]))
      .finally(() => setLoading(false))
  }

  const sentimentColor: Record<string, string> = {
    positive: "bg-green-100 text-green-700",
    neutral: "bg-gray-100 text-gray-600",
    negative: "bg-red-100 text-red-700",
  }

  const handleReply = async (commentId: string) => {
    const text = replyText[commentId]
    if (!text?.trim()) return
    try {
      await api.post(`/api/v1/comments/${commentId}/reply`, { text })
      setReplyText(prev => ({...prev, [commentId]: ""}))
      fetchComments()
    } catch {}
  }

  const handleHide = async (commentId: string) => {
    try {
      await api.post(`/api/v1/comments/${commentId}/hide`)
      fetchComments()
    } catch {}
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">인박스</h1>
        <button onClick={() => { setSyncing(true); api.post("/api/v1/comments/sync/all").finally(() => { setSyncing(false); fetchComments() }) }} disabled={syncing} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
          <RefreshCw size={14} className={syncing ? "animate-spin" : ""}/> 동기화
        </button>
      </div>
      {loading ? <p className="text-center text-gray-400">로딩 중...</p> : comments.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <MessageSquare size={48} className="mx-auto mb-4 opacity-30"/>
          <p>댓글이 없습니다</p>
        </div>
      ) : (
        <div className="space-y-3">
          {comments.filter(c => !c.is_hidden).map(c => (
            <div key={c.id} className="bg-white border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{c.author_name}</span>
                  {c.sentiment && <span className={`text-xs px-2 py-0.5 rounded-full ${sentimentColor[c.sentiment] || ""}`}>{c.sentiment}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{new Date(c.created_at).toLocaleDateString("ko")}</span>
                  <button onClick={() => handleHide(c.id)} className="text-gray-400 hover:text-red-500"><EyeOff size={14}/></button>
                </div>
              </div>
              <p className="text-sm text-gray-700 mb-3">{c.text}</p>
              <div className="flex gap-2">
                <input value={replyText[c.id] || ""} onChange={e => setReplyText(prev => ({...prev, [c.id]: e.target.value}))} placeholder="답글 작성..." className="flex-1 text-sm border rounded-lg px-3 py-1.5" onKeyDown={e => e.key === "Enter" && handleReply(c.id)}/>
                <button onClick={() => handleReply(c.id)} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"><Send size={14}/></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
