"use client"

import { useEffect } from 'react'
import { useComments } from '@/hooks/useComments'
import Link from 'next/link'

interface CommentsListProps {
  meetingId: number
}

export function CommentsList({ meetingId }: CommentsListProps) {
  const { comments, loading, error, fetchCommentsByMeetingId } = useComments()

  useEffect(() => {
    console.log("🧪 Fetching comments for meeting:", meetingId)
    fetchCommentsByMeetingId(meetingId)
  }, [meetingId, fetchCommentsByMeetingId])

  useEffect(() => {
    console.log("🧪 Fetched comments for meeting:", meetingId, comments)
  }, [comments, meetingId])

  if (loading) {
    return (
      <div className="py-2">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-rose-500 mx-auto"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-2 text-red-500 text-xs">
        {error}
      </div>
    )
  }

  if (comments.length === 0) {
    return (
      <div className="py-2 text-gray-500 text-xs">
        コメントはまだありません
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {comments.map((comment) => (
        <Link
          key={comment.comment_id}
          href={`/feedback/${meetingId}#comment-${comment.comment_id}`}
          className="block hover:bg-slate-50 transition-colors rounded p-2"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-600 mb-1">
                <span className="font-medium text-gray-900">{comment.user_name}</span>
              </p>
              <p className="text-gray-800 text-xs whitespace-pre-wrap break-words">
                {comment.content}
              </p>
            </div>
            <div className="ml-2 text-xs text-gray-500 shrink-0">
              {new Date(comment.inserted_datetime).toLocaleString('ja-JP', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
              })}
            </div>
          </div>
        </Link>
      ))}
    </div>
  )
} 