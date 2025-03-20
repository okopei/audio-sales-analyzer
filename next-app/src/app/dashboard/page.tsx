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

export default function Dashboard() {
  const { user, logout, isManager } = useAuth()
  const { userInfo, loading: userLoading } = useUser()
  const { meetings, loading, error } = useMeetings()
  const router = useRouter()
  
  // ログアウト処理
  const handleLogout = () => {
    logout()
  }

  const comments = [
    {
      id: 1,
      client: "株式会社ABC",
      comment: "予算について具体的な話し合いができました。次回は見積書を持参します。",
      commentTime: "02-07 15:30",
      isRead: false,
    },
    {
      id: 2,
      client: "DEF工業",
      comment: "技術的な課題について深い議論ができました。開発チームに確認が必要です。",
      commentTime: "02-07 13:00",
      isRead: true,
    },
    {
      id: 3,
      client: "GHIシステムズ",
      comment: "導入に前向きな反応でした。来週までに提案書を準備します。",
      commentTime: "02-06 16:30",
      isRead: false,
    },
  ]

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
              <div className="space-y-4">
                {comments.map((comment) => (
                  <div key={comment.id} className="block border-b last:border-0 pb-4 hover:bg-slate-50 rounded-lg transition-colors">
                    <Link href={`/feedback#${comment.id}`} className="block">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <div className="text-sm font-medium">佐藤部長</div>
                          <div className="text-sm text-gray-500">{comment.client}</div>
                        </div>
                        <div className="flex items-center gap-2">
                          {!comment.isRead && <Badge variant="destructive">未読</Badge>}
                          <span className="text-sm text-gray-500">{comment.commentTime}</span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600">{comment.comment}</p>
                    </Link>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}

