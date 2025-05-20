'use client'

import { useState, useEffect } from 'react'

interface User {
  user_id: number
  user_name: string
  email: string
  is_manager: boolean
  manager_name: string | null
  is_active: boolean
  account_status: string
}

interface AuthContext {
  user: User | null
  isLoading: boolean
  error: Error | null
}

export function useAuth(): AuthContext {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const fetchUser = async () => {
      try {
        // ローカルストレージからユーザー情報を取得
        const storedUser = localStorage.getItem('user')
        if (storedUser) {
          setUser(JSON.parse(storedUser))
        }
      } catch (err) {
        setError(err instanceof Error ? err : new Error('認証情報の取得に失敗しました'))
      } finally {
        setIsLoading(false)
      }
    }

    fetchUser()
  }, [])

  return { user, isLoading, error }
} 