"use client"

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from './useAuth'

interface Meeting {
  meeting_id: number
  title?: string
  client_contact_name: string
  client_company_name?: string
  meeting_datetime: string
  duration_seconds: number
  status: string
  transcript_text: string | null
  file_name: string | null
  file_size: number | null
  error_message: string | null
}

export function useMeetings() {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()

  const fetchMeetings = useCallback(async () => {
    if (!user) return

    try {
      setLoading(true)
      setError(null)

      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
      const response = await fetch(`${baseUrl}/meetings?userId=${user.user_id}`)
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      const data = await response.json()
      
      // APIレスポンスの形式をチェック（配列またはmeetingsプロパティを持つオブジェクト）
      const meetingsArray = Array.isArray(data) ? data : data.meetings || []
      
      // 日時でソートし、最新10件を取得
      const sortedMeetings = meetingsArray
        .sort((a: Meeting, b: Meeting) => 
          new Date(b.meeting_datetime).getTime() - new Date(a.meeting_datetime).getTime()
        )
        .slice(0, 10)
      
      setMeetings(sortedMeetings)
    } catch (err) {
      console.error("Error fetching meetings:", err)
      setError(`Error fetching meetings: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (user) {
      fetchMeetings()
      
      // 1分ごとに自動更新
      const intervalId = setInterval(() => {
        fetchMeetings()
      }, 60000)
      
      return () => clearInterval(intervalId)
    }
  }, [user, fetchMeetings])

  return {
    meetings,
    loading,
    error,
    refetch: fetchMeetings
  }
} 