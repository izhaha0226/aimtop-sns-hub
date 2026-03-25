"use client";

import { createContext, useCallback, useContext, useState } from "react";
import * as ToastPrimitive from "@radix-ui/react-toast";
import { cn } from "@/utils/cn";

type ToastVariant = "success" | "error" | "info";

interface ToastItem {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  toast: (item: Omit<ToastItem, "id">) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const VARIANT_STYLES: Record<ToastVariant, string> = {
  success: "border-green-500 bg-green-50 text-green-900",
  error: "border-red-500 bg-red-50 text-red-900",
  info: "border-blue-500 bg-blue-50 text-blue-900",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((item: Omit<ToastItem, "id">) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { ...item, id }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      <ToastPrimitive.Provider swipeDirection="right">
        {children}
        {toasts.map((t) => (
          <ToastElement key={t.id} item={t} onRemove={removeToast} />
        ))}
        <ToastPrimitive.Viewport className="fixed bottom-0 right-0 z-50 m-4 flex max-w-sm flex-col gap-2" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}

function ToastElement({
  item,
  onRemove,
}: {
  item: ToastItem;
  onRemove: (id: string) => void;
}) {
  return (
    <ToastPrimitive.Root
      className={cn(
        "rounded-md border-l-4 p-4 shadow-md",
        VARIANT_STYLES[item.variant]
      )}
      onOpenChange={(open) => {
        if (!open) onRemove(item.id);
      }}
    >
      <ToastPrimitive.Title className="text-sm font-semibold">
        {item.title}
      </ToastPrimitive.Title>
      {item.description ? (
        <ToastPrimitive.Description className="mt-1 text-xs">
          {item.description}
        </ToastPrimitive.Description>
      ) : null}
    </ToastPrimitive.Root>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}
