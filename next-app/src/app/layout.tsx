import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import type React from "react" // Import React
import { Toaster } from 'sonner'
import { AuthProvider } from '@/hooks/useAuth'


const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Audio Sales Analyzer",
  description: "営業支援AIエージェントアプリ",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body className={`${inter.className} min-h-screen bg-[#1F1F1F]`}>
        <AuthProvider>
          {children}
          <Toaster />
        </AuthProvider>
      </body>
    </html>
  )
}