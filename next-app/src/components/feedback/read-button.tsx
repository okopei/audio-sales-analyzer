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
    try {
      setIsLoading(true)
      console.log('[既読更新] リクエスト開始:', { commentId, userId })

      const requestBody = {
        comment_id: commentId,
        user_id: userId,
      }
      console.log('[既読更新] リクエストボディ:', requestBody)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/comments/read`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      console.log('[既読更新] レスポンスステータス:', response.status)
      const responseData = await response.json().catch(() => null)
      console.log('[既読更新] レスポンスデータ:', responseData)

      if (!response.ok) {
        throw new Error(responseData?.message || '既読の更新に失敗しました')
      }

      if (!responseData?.success) {
        throw new Error(responseData?.message || '既読の更新に失敗しました')
      }

      console.log('[既読更新] 成功:', responseData)
      onRead()
      toast.success('既読にしました')
    } catch (error) {
      console.error('[既読更新] エラー:', error)
      toast.error(error instanceof Error ? error.message : '既読の更新に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      disabled={isRead || isLoading}
      onClick={handleRead}
      className="text-xs text-muted-foreground hover:text-primary"
    >
      {isRead ? '既読済み' : '既読にする'}
    </Button>
  )
} 