"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'

// ユーザー情報の型定義
interface User {
  user_id: number
  email: string
  user_name: string
  account_status: string
  is_active: boolean
  is_manager?: boolean 
}

// 認証コンテキストの型定義
interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  isAuthenticated: boolean
  isManager: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(false) // middlewareで認証制御するためfalse
  const router = useRouter()
  const pathname = usePathname()

  const checkIsManager = (userData: User): boolean => userData.is_manager === true

  // 認証チェックをスキップするパス
  const skipAuthPaths = ['/', '/login', '/register']
  const skipFetch = skipAuthPaths.includes(pathname)

  // middlewareで認証制御するため、初期化時のfetch処理を削除
  useEffect(() => {
    if (skipFetch) {
      console.log('⏩ useAuth: ログイン不要ページなので認証チェックスキップ', pathname)
      return
    }

    // 状態復元処理：/api/auth/me を用いたリトライ戦略
    let attempt = 0
    const maxAttempts = 3

    const restoreUserState = async () => {
      try {
        const res = await fetch('/api/auth/me', {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`)
        }
        
        const data = await res.json()
        
        if (data?.user) {
          console.log('✅ ユーザー状態復元成功')
          setUser(data.user)
          return true
        } else {
          throw new Error('レスポンスにuser情報が含まれていません')
        }
      } catch (err) {
        console.warn(`⚠️ 状態復元試行 ${attempt + 1} 失敗:`, err)
        attempt++
        
        if (attempt < maxAttempts) {
          const delay = attempt * 1000 // 1秒 → 2秒 → 3秒
          setTimeout(restoreUserState, delay)
        } else {
          console.error('❌ ユーザー状態復元に失敗しました（最大試行回数到達）')
        }
        return false
      }
    }

    // 認証が必要なページでのみ状態復元を実行
    if (!skipFetch) {
      console.log('🔄 useAuth: 状態復元処理開始')
      restoreUserState()
    }
  }, [pathname, router, skipFetch])

  // ログイン処理
  const login = async (email: string, password: string) => {
    console.log('🔍 login処理開始:', { email })
    setLoading(true)
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      
      console.log('🔍 login API レスポンス status:', response.status)
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error('❌ login API エラー:', errorData)
        throw new Error(errorData.error || 'ログインに失敗しました')
      }
      
      const data = await response.json()
      console.log('✅ login API 成功:', data)
      
      const user = data.user
      if (user) {
        console.log('✅ user情報取得成功:', user)
        setUser(user)
        
        // ログイン成功後の画面遷移を追加
        console.log('✅ login 成功、router.push 実行予定')
        const isManager = checkIsManager(user)
        console.log('🔍 isManager判定:', isManager)
        
        if (isManager) {
          console.log('✅ マネージャーなので /manager-dashboard に遷移')
          router.push('/manager-dashboard')
        } else {
          console.log('✅ 一般ユーザーなので /dashboard に遷移')
          router.push('/dashboard')
        }
      } else {
        console.error('❌ user情報が含まれていません')
        setUser(null)
        throw new Error('ログイン応答にユーザー情報が含まれていません')
      }
    } catch (error) {
      console.error('❌ login処理でエラー:', error)
      setUser(null)
      throw error
    } finally {
      console.log('🔍 login処理完了、loading状態をfalseに')
      setLoading(false)
    }
  }

  // ログアウト処理
  const logout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' })
    } catch (error) {}
    setUser(null)
    router.push('/')
  }

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isManager: user ? checkIsManager(user) : false
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}