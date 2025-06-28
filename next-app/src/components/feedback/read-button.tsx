'use client'

import * as React from 'react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

interface ReadButtonProps {
  commentId: number
  userId: number
  isRead: boolean
  onRead: () => void
}

export function ReadButton({ commentId, userId, isRead, onRead }: ReadButtonProps) {
  const [isLoading, setIsLoading] = useState(false)

  const handleRead = async () => {
    if (isRead) return

    try {
      setIsLoading(true)
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/comments/read`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          comment_id: commentId,
          user_id: userId
        }),
      })

      if (!response.ok) {
        throw new Error('既読更新に失敗しました')
      }

      const data = await response.json()
      if (data.success) {
        onRead()
      } else {
        throw new Error(data.message || '既読更新に失敗しました')
      }
    } catch (error) {
      console.error('既読更新エラー:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      {!isRead && (
        <Button
          variant="ghost"
          size="sm"
          disabled={isLoading}
          onClick={handleRead}
          className="text-xs text-muted-foreground hover:text-primary"
        >
          {isLoading ? '処理中...' : '既読にする'}
        </Button>
      )}
    </>
  )
} 