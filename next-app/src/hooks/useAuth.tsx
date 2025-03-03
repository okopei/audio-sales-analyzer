"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'

// ユーザー情報の型定義
interface User {
  user_id: number
  email: string
  user_name: string
  is_manager: boolean
  role?: string  // roleフィールドを追加
}

// 認証コンテキストの型定義
interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  isManager: boolean
}

// 認証コンテキストの作成
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// APIのベースURL - 環境に応じて変更
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7071/api'

// ブラウザ環境かどうかを確認する関数
const isBrowser = () => typeof window !== 'undefined'

// 認証プロバイダーコンポーネント
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  // ユーザーがマネージャーかどうかを判定する関数
  const checkIsManager = (userData: User): boolean => {
    // is_managerフラグがtrueの場合、またはroleが'manager'の場合はマネージャー
    return userData.is_manager === true || userData.role === 'manager'
  }

  // 初期化時にローカルストレージからユーザー情報を取得
  useEffect(() => {
    const loadUserFromStorage = () => {
      try {
        if (isBrowser()) {
          const storedUser = localStorage.getItem('user')
          const storedToken = localStorage.getItem('token')
          
          if (storedUser && storedToken) {
            const parsedUser = JSON.parse(storedUser)
            
            // ユーザーデータにis_managerフラグがない場合、roleから設定
            if (parsedUser.role === 'manager' && parsedUser.is_manager !== true) {
              parsedUser.is_manager = true
            }
            
            setUser(parsedUser)
            
            // ユーザーがすでにログインしている場合、適切なダッシュボードにリダイレクト
            // ただし、現在のパスがダッシュボードまたはマネージャーダッシュボードの場合はリダイレクトしない
            const currentPath = window.location.pathname
            if (currentPath === '/') {
              if (checkIsManager(parsedUser)) {
                router.push('/manager-dashboard')
              } else {
                router.push('/dashboard')
              }
            }
          }
        }
      } catch (error) {
        console.error('Error loading user from storage:', error)
        // エラーが発生した場合はストレージをクリア
        if (isBrowser()) {
          localStorage.removeItem('user')
          localStorage.removeItem('token')
        }
      } finally {
        setLoading(false)
      }
    }
    
    loadUserFromStorage()
  }, [router])

  // ログイン処理
  const login = async (email: string, password: string) => {
    setLoading(true)
    
    try {
      console.log(`Attempting login for ${email}`)
      
      const response = await fetch(`${API_BASE_URL}/users/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'ログインに失敗しました')
      }
      
      const data = await response.json()
      console.log('Login successful:', data.user)
      
      // roleからis_managerフラグを設定
      if (data.user.role === 'manager' && data.user.is_manager !== true) {
        data.user.is_manager = true
      }
      
      // ローカルストレージに保存
      if (isBrowser()) {
        localStorage.setItem('token', data.token)
        localStorage.setItem('user', JSON.stringify(data.user))
      }
      
      setUser(data.user)
      
      // ユーザーの権限に基づいてリダイレクト
      if (checkIsManager(data.user)) {
        router.push('/manager-dashboard')
      } else {
        router.push('/dashboard')
      }
    } catch (error) {
      console.error('Login error:', error)
      throw error
    } finally {
      setLoading(false)
    }
  }

  // ログアウト処理
  const logout = () => {
    if (isBrowser()) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
    setUser(null)
    router.push('/')
  }

  // コンテキスト値の作成
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

// カスタムフック
export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}