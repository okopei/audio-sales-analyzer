'use client'

import * as React from 'react'
import { Comment } from '@/types/comment'
import { ReadButton } from './read-button'
import { useAuth } from '@/hooks/useAuth'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CommentListProps {
  comments: Comment[]
  onCommentRead: (commentId: number) => void
  onDeleteComment?: (commentId: number) => void
}

export function CommentList({ comments, onCommentRead, onDeleteComment }: CommentListProps) {
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
          
          <div className="absolute bottom-2 right-2 flex items-center gap-2">
            {comment.user_id === currentUserId && onDeleteComment && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDeleteComment(comment.comment_id)}
                className="text-xs text-red-500 hover:text-red-600 hover:bg-red-50"
              >
                <Trash2 size={14} className="mr-1" />
                削除
              </Button>
            )}
            {comment.user_id !== currentUserId && (
              <ReadButton
                commentId={comment.comment_id}
                userId={currentUserId}
                isRead={comment.readers.some(reader => reader.reader_id === currentUserId)}
                onRead={() => onCommentRead(comment.comment_id)}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  )
} 