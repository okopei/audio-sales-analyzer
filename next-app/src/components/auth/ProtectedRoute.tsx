"use client"

import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

interface ProtectedRouteProps {
  children: React.ReactNode
  requireManager?: boolean
}

export default function ProtectedRoute({ 
  children, 
  requireManager = false 
}: ProtectedRouteProps) {
  const { isAuthenticated, isManager, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        router.push('/') // ホームページへリダイレクト
      } else if (requireManager && !isManager) {
        router.push('/dashboard') // 一般ユーザー向けページにリダイレクト
      }
    }
  }, [isAuthenticated, isManager, loading, requireManager, router])

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
    </div>
  }

  if (!isAuthenticated || (requireManager && !isManager)) {
    return null
  }

  return <>{children}</>
}