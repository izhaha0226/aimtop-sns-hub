"use client"
import { useEffect } from "react"
import { X } from "lucide-react"
import { cn } from "@/utils/cn"

interface ToastProps {
  message: string
  type?: "success" | "error" | "info"
  onClose: () => void
}

export function Toast({ message, type = "info", onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className={cn(
      "fixed bottom-4 right-4 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm text-white z-50",
      type === "success" && "bg-green-600",
      type === "error" && "bg-red-600",
      type === "info" && "bg-blue-600",
    )}>
      <span>{message}</span>
      <button onClick={onClose} className="hover:opacity-70">
        <X size={14} />
      </button>
    </div>
  )
}
