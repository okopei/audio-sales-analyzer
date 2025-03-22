import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import type React from "react" // Import React
import { Toaster as SonnerToaster } from 'sonner'
import { Toaster as HotToaster } from 'react-hot-toast'
import ClientProviders from '@/components/ClientProviders'

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
        <ClientProviders>
          {children}
          <SonnerToaster />
          <HotToaster position="top-center" />
        </ClientProviders>
      </body>
    </html>
  )
}