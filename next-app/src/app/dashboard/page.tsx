"use client"

import React, { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Search, PlusCircle, LogOut, Users } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useAuth } from "@/hooks/useAuth"
import { useUser } from "@/hooks/useUser"
import { useMeetings } from "@/hooks/useMeetings"
import ProtectedRoute from "@/components/auth/ProtectedRoute"
import { getLatestComments } from "@/lib/api/feedback"
import { DashboardCommentList } from '@/components/dashboard/comment-list'
import { toast } from 'sonner'
import { format } from 'date-fns'
import { ja } from 'date-fns/locale'
import { ReadButton } from '@/components/feedback/read-button'

interface LatestComment {
  comment_id: number
  segment_id: number
  meeting_id: number
  user_id: number
  user_name: string
  content: string
  inserted_datetime: string
  updated_datetime: string
  client_company_name?: string
  client_contact_name?: string
  isRead: boolean
}

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
  readers: Array<{
    reader_id: number
    read_datetime: string
  }>
}

export default function Dashboard() {
  const { user, logout, isManager } = useAuth()
  const { userInfo, loading: userLoading } = useUser()
  const { meetings, loading, error } = useMeetings()
  const router = useRouter()
  const [latestComments, setLatestComments] = useState<LatestComment[]>([])
  const [commentsLoading, setCommentsLoading] = useState(true)
  const [comments, setComments] = useState<Comment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  
  // ログアウト処理
  const handleLogout = () => {
    logout()
  }

  // 最新のコメントを取得
  useEffect(() => {
    const fetchLatestComments = async () => {
      if (!user?.user_id) {
        console.log('ユーザーIDが存在しないため、コメント取得をスキップします')
        setLatestComments([])
        setCommentsLoading(false)
        return
      }

      try {
        setCommentsLoading(true)
        console.log('=== コメント取得デバッグ情報 ===')
        console.log('ログインユーザー情報:', {
          user_id: user.user_id,
          user_name: user.user_name,
          email: user.email
        })
        
        const userId = user.user_id
        console.log('API呼び出しに使用するuser_id:', userId)
        
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/comments-latest?userId=${userId}`)
        const data = await response.json()
        console.log('APIレスポンスデータ:', data)
        
        if (Array.isArray(data)) {
          setLatestComments(data)
        } else {
          throw new Error('コメント形式が不正です')
        }
      } catch (error) {
        console.error('最新コメント取得エラー:', error)
        setLatestComments([])
      } finally {
        setCommentsLoading(false)
      }
    }

    fetchLatestComments()
  }, [user?.user_id]) // user全体ではなく、user_idのみを依存配列に設定

  const fetchComments = async () => {
    if (!user?.user_id) return

    try {
      setIsLoading(true)
      console.log('[コメント取得] 開始:', { userId: user.user_id })

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/comments-latest?userId=${user.user_id}`
      )
      console.log('[コメント取得] レスポンスステータス:', response.status)

      const data = await response.json()
      console.log('[コメント取得] レスポンスデータ:', data)

      if (!response.ok) {
        throw new Error(data.message || 'コメントの取得に失敗しました')
      }

      if (Array.isArray(data)) {
        setComments(data)
      } else {
        throw new Error('コメント形式が不正です')
      }
    } catch (error) {
      console.error('[コメント取得] エラー:', error)
      toast.error(error instanceof Error ? error.message : 'コメントの取得に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (user?.user_id) {
      fetchComments()
    }
  }, [user?.user_id]) // user_idのみを依存配列に設定

  const handleCommentRead = () => {
    fetchComments()
  }

  // 日付をフォーマットする関数
  const formatDateTime = (dateTimeStr: string) => {
    const date = new Date(dateTimeStr)
    return date.toLocaleDateString("ja-JP", {
      month: "2-digit",
      day: "2-digit"
    })
  }

  // 所要時間を表示用にフォーマットする関数
  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) {
      return `${minutes}分`
    }
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return `${hours}時間${remainingMinutes > 0 ? `${remainingMinutes}分` : ''}`
  }

  // コメント日時を表示用にフォーマットする関数
  const formatCommentTime = (dateTimeStr: string) => {
    const date = new Date(dateTimeStr)
    return date.toLocaleDateString("ja-JP", {
      month: "2-digit",
      day: "2-digit"
    }) + " " + date.toLocaleTimeString("ja-JP", {
      hour: "2-digit",
      minute: "2-digit"
    })
  }

  if (!user) {
    return (
      <div className="container mx-auto p-4">
        <p className="text-center text-muted-foreground">ログインが必要です</p>
      </div>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-zinc-50 p-4 sm:p-6">
        {/* ヘッダー */}
        <div className="mb-6">
          {/* ユーザー名とログアウトボタン */}
          <div className="flex justify-between items-center mb-4">
            <div className="text-xl font-medium">
              {userInfo?.user_name || user?.user_name || "ユーザー"} 様
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleLogout}
              className="text-sm text-rose-500 border-rose-200 hover:bg-rose-50"
            >
              <LogOut className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">ログアウト</span>
            </Button>
          </div>
          
          {/* アクションボタン */}
          <div className="flex items-center justify-center gap-2 flex-wrap">
            <Link href="/search">
              <Button variant="outline" size="sm" className="text-sm">
                <Search className="w-4 h-4 mr-2" />
                商談検索
              </Button>
            </Link>
            <Link href="/newmeeting">
              <Button variant="outline" size="sm" className="text-sm">
                <PlusCircle className="w-4 h-4 mr-2" />
                新規商談
              </Button>
            </Link>
            {isManager && (
              <Link href="/manager-dashboard">
                <Button variant="outline" size="sm" className="text-sm bg-green-50 border-green-200 text-green-600 hover:bg-green-100">
                  <Users className="w-4 h-4 mr-2" />
                  メンバー管理
                </Button>
              </Link>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 面談一覧 */}
          <Card className="p-4 sm:p-6">
            <h2 className="text-lg sm:text-xl font-semibold mb-4">過去商談一覧</h2>
            {error && (
              <div className="text-sm text-red-500 mb-4">
                {error}
              </div>
            )}
            <ScrollArea className="h-[300px] sm:h-[600px]">
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-rose-500"></div>
                </div>
              ) : meetings.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[200px] text-gray-500">
                  <p className="mb-2">商談データがありません</p>
                  <Link href="/newmeeting">
                    <Button variant="outline" size="sm" className="text-sm">
                      <PlusCircle className="w-4 h-4 mr-2" />
                      新規商談を作成
                    </Button>
                  </Link>
                </div>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="border-b text-sm">
                      <th className="text-left pb-2 pr-4">日付</th>
                      <th className="text-left pb-2 pr-4">顧客名</th>
                      <th className="text-left pb-2">所要時間</th>
                    </tr>
                  </thead>
                  <tbody>
                    {meetings.map((meeting) => (
                      <tr key={meeting.meeting_id} className="border-b last:border-0 hover:bg-slate-50 transition-colors">
                        <td className="py-3 pr-4">
                          <Link href={`/feedback/${meeting.meeting_id}`} className="block">
                            {formatDateTime(meeting.meeting_datetime)}
                          </Link>
                        </td>
                        <td className="py-3 pr-4">
                          <Link href={`/feedback/${meeting.meeting_id}`} className="block">
                            <div className="flex flex-col">
                              <span>{meeting.client_contact_name || '(名前なし)'}</span>
                              {meeting.client_company_name && (
                                <span className="text-xs text-gray-500">{meeting.client_company_name}</span>
                              )}
                            </div>
                          </Link>
                        </td>
                        <td className="py-3">
                          <Link href={`/feedback/${meeting.meeting_id}`} className="block">
                            {formatDuration(meeting.duration_seconds)}
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </ScrollArea>
          </Card>

          {/* 最新のコメント */}
          <Card className="p-4 sm:p-6">
            <h2 className="text-lg sm:text-xl font-semibold mb-4">最新のコメント</h2>
            <ScrollArea className="h-[300px] sm:h-[600px]">
              {isLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-rose-500"></div>
                </div>
              ) : comments.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[200px] text-gray-500">
                  <p>コメントデータがありません</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {comments.map((comment) => {
                    const isRead = comment.readers?.some(reader => reader.reader_id === user?.user_id) ?? false
                    const isOwnComment = comment.user_id === user?.user_id

                    return (
                      <div
                        key={comment.comment_id}
                        className="block border-b last:border-0 pb-4 hover:bg-slate-50 rounded-lg transition-colors"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <Link
                            href={`/feedback/${comment.meeting_id}?segment=${comment.segment_id}`}
                            className="flex-1"
                          >
                            <div>
                              <div className="text-sm font-medium">{comment.user_name}</div>
                              <div className="text-sm text-gray-500">
                                {comment.client_company_name && `${comment.client_company_name} - `}
                                {comment.client_contact_name || '顧客名なし'}
                              </div>
                            </div>
                            <p className="text-sm text-gray-600 mt-2">{comment.content}</p>
                          </Link>
                          <div className="flex items-center gap-2 ml-4">
                            {!isOwnComment && user?.user_id && (
                              <ReadButton
                                commentId={comment.comment_id}
                                userId={user.user_id}
                                isRead={isRead}
                                onRead={handleCommentRead}
                              />
                            )}
                            <span className="text-sm text-gray-500">
                              {format(new Date(comment.inserted_datetime), 'yyyy/MM/dd HH:mm', { locale: ja })}
                            </span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </ScrollArea>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}

