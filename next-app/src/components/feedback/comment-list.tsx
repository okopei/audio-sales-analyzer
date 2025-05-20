'use client'

import * as React from 'react'
import { Comment } from '@/types/comment'
import { ReadButton } from './read-button'
import { useAuth } from '@/hooks/useAuth'

interface CommentListProps {
  comments: Comment[]
  onCommentRead: (commentId: number) => void
}

export function CommentList({ comments, onCommentRead }: CommentListProps) {
  const { user } = useAuth()
  const currentUserId = user?.user_id

  if (!currentUserId) return null

  return (
    <div className="space-y-4">
      {comments.map((comment) => (
        <div key={comment.comment_id} className="relative rounded-lg border p-4">
          <div className="mb-2 text-sm text-muted-foreground">
            {comment.user_name} • {new Date(comment.inserted_datetime).toLocaleString()}
          </div>
          <p className="text-sm">{comment.content}</p>
          
          {comment.user_id !== currentUserId && (
            <div className="absolute bottom-2 right-2">
              <ReadButton
                commentId={comment.comment_id}
                userId={currentUserId}
                isRead={comment.readers.some(reader => reader.reader_id === currentUserId)}
                onRead={() => onCommentRead(comment.comment_id)}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  )
} 