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
    if (!loading && !redirecting) {
      if (!isAuthenticated) {
        setRedirecting(true)
        console.log('User is not authenticated, redirecting to home')
        // 遅延を入れてリダイレクトを確実に実行
        setTimeout(() => {
          router.push('/')
        }, 100)
      } else if (requireManager && !isManager) {
        setRedirecting(true)
        console.log('User is not a manager, redirecting to dashboard', user)
        // 遅延を入れてリダイレクトを確実に実行
        setTimeout(() => {
          router.push('/dashboard')
        }, 100)
      }
    }
  }, [isAuthenticated, isManager, loading, requireManager, router, user, redirecting])

  if (loading || redirecting) {
    return <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
    </div>
  }

  if (!isAuthenticated || (requireManager && !isManager)) {
    return null
  }

  return <>{children}</>
}