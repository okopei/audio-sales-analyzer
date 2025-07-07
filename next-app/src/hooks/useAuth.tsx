"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import Cookies from 'js-cookie'

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
  logout: () => void
  isAuthenticated: boolean
  isManager: boolean
}

// 認証コンテキストの作成
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// ブラウザ環境かどうかを確認する関数
const isBrowser = () => typeof window !== 'undefined'

// Cookieの有効期限（7日間）
const COOKIE_EXPIRY = 7

// 認証プロバイダーコンポーネント
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  // ユーザーがマネージャーかどうかを判定する関数
  const checkIsManager = (userData: User): boolean => {
    return userData.is_manager === true
  }

  // 初期化時にCookieとローカルストレージからユーザー情報を取得
  useEffect(() => {
    const loadUserFromStorage = () => {
      try {
        if (isBrowser()) {
          // まず、Cookieから取得を試みる
          let storedUser = Cookies.get('user')
          let storedToken = Cookies.get('authToken')
          
          // Cookieになければローカルストレージから取得
          if (!storedUser || !storedToken) {
            storedUser = localStorage.getItem('user') ?? undefined
            storedToken = localStorage.getItem('token') ?? undefined
            
            // ローカルストレージにあればCookieにも保存
            if (storedUser && storedToken) {
              Cookies.set('user', storedUser, { expires: COOKIE_EXPIRY })
              Cookies.set('authToken', storedToken, { expires: COOKIE_EXPIRY })
            }
          }
          
          if (storedUser && storedToken) {
            const parsedUser = JSON.parse(storedUser)
            
            // ユーザーデータにaccount_statusがない場合、roleから設定
            if (parsedUser.is_manager === true && parsedUser.account_status !== 'ACTIVE') {
              parsedUser.account_status = 'ACTIVE'
            }
            
            setUser(parsedUser)
            
            // ユーザーがすでにログインしている場合、適切なダッシュボードにリダイレクト
            // ただし、現在のパスがダッシュボードまたはマネージャーダッシュボードの場合はリダイレクトしない
            const currentPath = window.location.pathname
            if (currentPath === '/') {
              // リダイレクト前に少し遅延を入れて、Reactの状態更新が反映されるようにする
              setTimeout(() => {
                if (checkIsManager(parsedUser)) {
                  router.push('/manager-dashboard')
                } else {
                  router.push('/dashboard')
                }
              }, 100)
            }
          }
        }
      } catch (error) {
        console.error('Error loading user from storage:', error)
        // エラーが発生した場合はストレージをクリア
        if (isBrowser()) {
          localStorage.removeItem('user')
          localStorage.removeItem('token')
          Cookies.remove('user')
          Cookies.remove('authToken')
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
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/users/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'ログインに失敗しました')
    }

    const data = await response.json()
    const user = data.user  

    if (isBrowser()) {
      localStorage.setItem('token', data.token ?? '')
      localStorage.setItem('user', JSON.stringify(user))
      Cookies.set('authToken', data.token ?? '', { expires: COOKIE_EXPIRY })
      Cookies.set('user', JSON.stringify(user), { expires: COOKIE_EXPIRY })
    }

    setUser(user)

    // is_manager フラグに応じて遷移
    setTimeout(() => {
      const isManager =
        user.is_manager === true ||
        user.is_manager === 'TRUE' ||
        user.is_manager === 1

      console.log('👉 isManager 判定:', isManager, '元の値:', user.is_manager, typeof user.is_manager)

      if (isManager) {
        router.push('/manager-dashboard')
      } else {
        router.push('/dashboard')
      }
    }, 100)
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
      // ローカルストレージから削除
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      
      // Cookieからも削除
      Cookies.remove('authToken')
      Cookies.remove('user')
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