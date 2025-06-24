"use client"

import { useState, useCallback } from 'react'

interface Comment {
  comment_id: number
  meeting_id: number
  user_id: number
  user_name: string
  content: string
  inserted_datetime: string
  updated_datetime: string | null
}

export function useComments() {
  const [comments, setComments] = useState<Comment[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchCommentsByMeetingId = useCallback(async (meetingId: number) => {
    try {
      setLoading(true)
      setError(null)

      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
      const url = `${baseUrl}/comments/by-meeting/${meetingId}`
      
      console.log("🔗 Fetching comments from:", url)

      const response = await fetch(url)
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error("❌ API Error Response:", errorData)
        throw new Error(errorData.error || `API error: ${response.status}`)
      }

      const data = await response.json()
      console.log("📝 Fetched comments count:", data.length)
      
      if (!Array.isArray(data)) {
        throw new Error("Invalid response format")
      }

      setComments(data)
    } catch (err) {
      setError(`Error fetching comments: ${err instanceof Error ? err.message : String(err)}`)
      setComments([])
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    comments,
    loading,
    error,
    fetchCommentsByMeetingId
  }
} 