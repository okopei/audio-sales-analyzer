'use client'

import * as React from 'react'
import { useAuth } from '@/hooks/useAuth'
import { ReadButton } from '@/components/feedback/read-button'
import { Badge } from '@/components/ui/badge'
import { format } from 'date-fns'
import { ja } from 'date-fns/locale'

interface Comment {
  comment_id: number
  segment_id: number
  meeting_id: number
  user_id: number
  content: string
  inserted_datetime: string
  updated_datetime: string
  user_name: string
  client_company_name: string
  client_contact_name: string
  isRead?: boolean
  readers?: Array<{
    reader_id: number
    read_datetime: string
  }>
}

interface DashboardCommentListProps {
  comments: Comment[]
  onCommentRead: () => void
}

export function DashboardCommentList({ comments, onCommentRead }: DashboardCommentListProps) {
  const { user } = useAuth()
  const currentUserId = user?.user_id

  if (!currentUserId) return null

  return (
    <div className="space-y-4">
      {comments.map((comment) => {
        const isRead = comment.isRead ?? comment.readers?.some(reader => reader.reader_id === currentUserId) ?? false
        const isOwnComment = comment.user_id === currentUserId

        return (
          <div
            key={comment.comment_id}
            className="rounded-lg border bg-card p-4 shadow-sm"
          >
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{comment.user_name}</span>
                  {comment.isRead !== undefined && (
                    comment.isRead ? (
                      <Badge variant="secondary" className="ml-2">既読済み</Badge>
                    ) : (
                      <Badge variant="outline" className="ml-2 text-red-500 border-red-300">未読</Badge>
                    )
                  )}
                  <span className="text-sm text-muted-foreground">
                    {format(new Date(comment.inserted_datetime), 'yyyy/MM/dd HH:mm', { locale: ja })}
                  </span>
                </div>
                <div className="text-sm text-muted-foreground">
                  {comment.client_company_name} - {comment.client_contact_name}
                </div>
                <p className="mt-2 text-sm">{comment.content}</p>
              </div>
              {!isOwnComment && (
                <ReadButton
                  commentId={comment.comment_id}
                  userId={currentUserId}
                  isRead={isRead}
                  onRead={onCommentRead}
                />
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
} 