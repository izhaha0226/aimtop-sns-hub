import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "AimTop SNS Hub",
  description: "멀티 클라이언트 SNS 자동화 플랫폼",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  )
}
