"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Search, PlusCircle, LogOut, User } from "lucide-react"
import Link from "next/link"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useAuth } from "@/hooks/useAuth"
import { useUser } from "@/hooks/useUser"
import { useMembersMeetings } from "@/hooks/useMembersMeetings"
import React, { useState, useEffect } from "react"
import ProtectedRoute from "@/components/auth/ProtectedRoute"
import { CommentsList } from '@/components/comments/CommentsList'
import { DashboardCommentList } from '@/components/dashboard/comment-list'
import { toast } from '@/components/ui/use-toast'

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
  isRead?: boolean
}

export default function ManagerDashboard() {
  const { user, logout } = useAuth()
  const { userInfo, loading: userLoading } = useUser()
  const { meetings, loading, error } = useMembersMeetings()
  const [comments, setComments] = useState<Comment[]>([])
  const [loadingComments, setLoadingComments] = useState(false)
  const [hasLogged, setHasLogged] = useState(false)

  // デバッグログを初回マウント時のみ出力
  useEffect(() => {
    if (!hasLogged) {
      console.log("🔍 ManagerDashboard Debug:", {
        user: user,
        userInfo: userInfo,
        userLoading: userLoading,
        meetings: meetings,
        loading: loading,
        error: error,
        NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL
      })
      setHasLogged(true)
    }
  }, [user, userInfo, userLoading, meetings, loading, error, hasLogged])

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

  // ログアウト処理
  const handleLogout = () => {
    logout()
  }

  // コメントを取得する関数
  const fetchComments = async () => {
    if (!user?.user_id) {
      console.warn("⚠️ user_id が無効です:", user)
      return
    }

    console.log("✅ fetchComments 実行: user_id =", user.user_id)

    setLoadingComments(true)
    try {
      const url = `${process.env.NEXT_PUBLIC_API_BASE_URL}/comments-latest?userId=${user.user_id}&isManager=true`
      console.log("🔍 リクエストURL:", url)

      const response = await fetch(url)

      console.log("📦 レスポンス status:", response.status)
      const data = await response.json()
      console.log("📨 レスポンス JSON:", data)

      if (!response.ok) throw new Error(data.message || 'コメントの取得に失敗しました')
      if (!Array.isArray(data)) throw new Error('コメント形式が不正です')

      // 🧠 各コメントに isRead を付加する
      const commentsWithReadStatus = await Promise.all(data.map(async (comment: Comment) => {
        try {
          const readStatusRes = await fetch(
            `${process.env.NEXT_PUBLIC_API_BASE_URL}/comment-read-status?userId=${user.user_id}&commentId=${comment.comment_id}`, 
            {
              method: 'GET',
              credentials: 'include'
            }
          )
          const readStatus = await readStatusRes.json()
          return {
            ...comment,
            isRead: readStatus?.isRead ?? false
          }
        } catch (e) {
          console.warn("📛 既読ステータス取得失敗:", e)
          return {
            ...comment,
            isRead: false
          }
        }
      }))

      console.log("🧾 コメント一覧 + isRead:", commentsWithReadStatus)
      setComments(commentsWithReadStatus)
    } catch (error) {
      console.error('❌ コメント取得エラー:', error)
      toast({
        title: 'エラー',
        description: error instanceof Error ? error.message : 'コメントの取得に失敗しました',
        variant: 'destructive'
      })
    } finally {
      setLoadingComments(false)
    }
  }

  // コメントが既読になった時の処理
  const handleCommentRead = () => {
    fetchComments()
  }

  useEffect(() => {
    console.log('ログイン中のuser_id:', user?.user_id)
    console.log('Usersテーブル検索結果:', userInfo)
    console.log('user_name:', userInfo?.user_name ?? user?.user_name)
    if (user?.user_id) {
      fetchComments()
    }
  }, [user?.user_id, userInfo])

  // middlewareで認証制御されるため、userがnullの場合は表示しない
  // 未認証の場合はmiddlewareでリダイレクトされる

  return (
    <ProtectedRoute requireManager={true}>
      <div className="min-h-screen bg-zinc-50 p-4 sm:p-6">
        {/* ヘッダー */}
        <div className="mb-6">
          {/* ユーザー名とログアウトボタン */}
          <div className="flex justify-between items-center mb-4">
            <div className="text-xl font-medium">
              {userInfo?.user_name ? `${userInfo.user_name}様` : (user?.user_name ? `${user.user_name}様` : 'MGR')}
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
            <Link href="/dashboard">
              <Button variant="outline" size="sm" className="text-sm bg-blue-50 border-blue-200 text-blue-600 hover:bg-blue-100">
                <User className="w-4 h-4 mr-2" />
                自分の商談
              </Button>
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 面談一覧 */}
          <Card className="p-4 sm:p-6">
            <h2 className="text-lg sm:text-xl font-semibold mb-4">メンバー商談一覧</h2>
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
                  <p className="mb-2">メンバーの商談データがありません</p>
                </div>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="border-b text-sm">
                      <th className="text-left pb-2 pr-4">日付</th>
                      <th className="text-left pb-2 pr-4">顧客</th>
                      <th className="text-left pb-2">営業担当</th>
                    </tr>
                  </thead>
                  <tbody>
                    {meetings.map((meeting) => (
                      <tr 
                        key={meeting.meeting_id} 
                        className="border-b last:border-0 hover:bg-slate-50 transition-colors"
                      >
                        <td className="py-3 pr-4">
                          <Link href={`/feedback/${meeting.meeting_id}`} className="block">
                            {formatDateTime(meeting.meeting_datetime)}
                          </Link>
                        </td>
                        <td className="py-3 pr-4">
                          <Link href={`/feedback/${meeting.meeting_id}`} className="block">
                            <div className="flex flex-col">
                              <span>{meeting.client_contact_name}</span>
                              <span className="text-xs text-gray-500">{meeting.client_company_name}</span>
                            </div>
                          </Link>
                        </td>
                        <td className="py-3">
                          <Link href={`/feedback/${meeting.meeting_id}`} className="block">
                            <span className="font-medium text-blue-600">{meeting.user_name || "不明"}</span>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </ScrollArea>
          </Card>

          {/* コメント一覧 */}
          <Card className="p-4 sm:p-6">
            <h2 className="text-lg sm:text-xl font-semibold mb-4">コメント一覧</h2>
            <ScrollArea className="h-[300px] sm:h-[600px]">
              {loadingComments ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-rose-500"></div>
                </div>
              ) : comments.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[200px] text-gray-500">
                  <p className="mb-2">コメントはありません</p>
                </div>
              ) : (
                <DashboardCommentList
                  comments={comments}
                  onCommentRead={handleCommentRead}
                />
              )}
            </ScrollArea>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}


