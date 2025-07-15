"use client"

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from './useAuth'

interface Meeting {
  meeting_id: number
  user_id: number
  user_name: string  // メンバー名を表示するために追加
  title?: string     // 任意に変更
  client_contact_name: string  // 追加
  client_company_name?: string  // 企業名を追加
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
    if (!user) {
      console.log("❌ useMembersMeetings: user is null")
      return
    }

    try {
      setLoading(true)
      setError(null)

      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:7071'
      const url = `${baseUrl}/members-meetings?manager_id=${user.user_id}`
      
      console.log("🔗 Fetching from:", url)
      console.log("✅ useMembersMeetings manager_id:", user.user_id)
      console.log("🔍 baseUrl:", baseUrl)

      const response = await fetch(url)
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error("❌ API Error Response:", errorData)
        throw new Error(errorData.error || `API error: ${response.status}`)
      }

      const data = await response.json()
      console.log("📊 Fetched meetings count:", data.length)
      
      // データの存在確認とエラーハンドリング
      if (!data || !Array.isArray(data)) {
        setError("APIからのレスポンスが不正です")
        setMeetings([])
        return
      }
      
      // ステータスが'AllStepCompleted'の会議のみをフィルタリング
      const completedMeetings = data.filter((meeting: Meeting) => 
        meeting.status === 'AllStepCompleted'
      )
      
      // 日時でソートし、最新10件を取得
      const sortedMeetings = completedMeetings
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
    if (user?.user_id) {
      fetchMembersMeetings()
      
      // 1分ごとに自動更新
      const intervalId = setInterval(() => {
        fetchMembersMeetings()
      }, 60000)
      
      return () => clearInterval(intervalId)
    }
  }, [user?.user_id, fetchMembersMeetings])

  return {
    meetings,
    loading,
    error,
    refetch: fetchMembersMeetings
  }
} 