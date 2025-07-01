"use client"

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from './useAuth'

// ユーザー情報の型定義
interface User {
  user_id: number
  user_name: string
  email: string
  role: string
  is_active: boolean
  account_status: string
  manager_name?: string
}

/**
 * ユーザー情報を取得するカスタムフック
 * ログインしているユーザーのIDを使用して、最新のユーザー情報をAPIから取得します。
 */
export function useUser() {
  const [userInfo, setUserInfo] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()

  const fetchUser = useCallback(async () => {
    if (!user?.user_id) return

    try {
      setLoading(true)
      setError(null)

      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:7071'
      const response = await fetch(`${baseUrl}/users/id/${user.user_id}`)
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      const data = await response.json()
      // userプロパティがなければフラットなdataをそのまま使う
      const userObj = data.user ?? data
      if (!userObj || !userObj.user_name) {
        console.error('Users APIレスポンスが不正です:', data)
        setError('Users APIレスポンスが不正です')
        setUserInfo(null)
        return
      }
      setUserInfo(userObj)
    } catch (err) {
      console.error("Error fetching user info:", err)
      setError(`Error fetching user info: ${err instanceof Error ? err.message : String(err)}`)
      // エラー時には認証情報のユーザー名をフォールバックとして使用
      if (user) {
        setUserInfo({
          user_id: user.user_id,
          user_name: user.user_name,
          email: user.email,
          role: user.role || 'member',
          is_active: true,
          account_status: 'active'
        })
      }
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (user?.user_id) {
      fetchUser()
    }
  }, [user, fetchUser])

  return {
    userInfo,
    loading,
    error,
    refetch: fetchUser
  }
} 