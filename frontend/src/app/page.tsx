"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    const hasToken =
      typeof window !== "undefined" &&
      !!localStorage.getItem("access_token");

    if (hasToken) {
      router.replace("/dashboard");
    } else {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center">
      <LoadingSpinner size="lg" />
    </div>
  );
}
