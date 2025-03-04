"use client"

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from './useAuth'

interface Meeting {
  meeting_id: number
  user_id: number
  user_name: string  // メンバー名を表示するために追加
  title?: string     // 任意に変更
  client_contact_name: string  // 追加
  meeting_datetime: string
  duration_seconds: number
  status: string
  transcript_text: string | null
  file_name: string | null
  file_size: number | null
  error_message: string | null
}

export function useMembersMeetings() {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()

  const fetchMembersMeetings = useCallback(async () => {
    if (!user) return

    try {
      setLoading(true)
      setError(null)

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7071/api'
      const url = `${baseUrl}/members-meetings?manager_id=${user.user_id}`
      
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      const data = await response.json()
      
      // データの存在確認とエラーハンドリング
      if (!data) {
        setError("APIからのレスポンスが空です")
        setMeetings([])
        return
      }
      
      if (data.error) {
        setError(`APIエラー: ${data.error}`)
        setMeetings([])
        return
      }
      
      if (data.message && !data.meetings) {
        // エラーではなく情報メッセージとして扱う
        setMeetings([])
        return
      }
      
      if (!data.meetings) {
        setError("APIからのレスポンスに会議データが含まれていません")
        setMeetings([])
        return
      }
      
      // 日時でソートし、最新10件を取得
      const sortedMeetings = data.meetings
        .sort((a: Meeting, b: Meeting) => 
          new Date(b.meeting_datetime).getTime() - new Date(a.meeting_datetime).getTime()
        )
        .slice(0, 10)
      
      setMeetings(sortedMeetings)
    } catch (err) {
      setError(`Error fetching members meetings: ${err instanceof Error ? err.message : String(err)}`)
      setMeetings([])
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (user) {
      fetchMembersMeetings()
      
      // 1分ごとに自動更新
      const intervalId = setInterval(() => {
        fetchMembersMeetings()
      }, 60000)
      
      return () => clearInterval(intervalId)
    }
  }, [user, fetchMembersMeetings])

  return {
    meetings,
    loading,
    error,
    refetch: fetchMembersMeetings
  }
} 