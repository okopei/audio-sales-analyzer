"use client"

import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

interface ProtectedRouteProps {
  children: React.ReactNode
  requireManager?: boolean
}

export default function ProtectedRoute({ 
  children, 
  requireManager = false 
}: ProtectedRouteProps) {
  const { isAuthenticated, isManager, loading, user } = useAuth()
  const router = useRouter()
  const [redirecting, setRedirecting] = useState(false)

  useEffect(() => {
    console.log("🔍 ProtectedRoute Debug:", {
      loading,
      redirecting,
      isAuthenticated,
      isManager,
      requireManager,
      user
    })
    
    // middlewareで認証制御されるため、基本的には何もしない
    // ただし、マネージャー権限チェックは残す
    if (!loading && !redirecting && requireManager && isAuthenticated && !isManager) {
      setRedirecting(true)
      console.log('User is not a manager, redirecting to dashboard', user)
      setTimeout(() => {
        router.push('/dashboard')
      }, 100)
    }
  }, [isAuthenticated, isManager, loading, requireManager, router, user, redirecting])

  // ローディング中またはリダイレクト中
  if (loading || redirecting) {
    return <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
    </div>
  }

  // マネージャー権限が必要だが持っていない場合のみチェック
  if (requireManager && isAuthenticated && !isManager) {
    return null
  }

  return <>{children}</>
}