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

export default function ManagerDashboard() {
  const { user, logout } = useAuth()
  const { userInfo, loading: userLoading } = useUser()
  const { meetings, loading, error } = useMembersMeetings()

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

  useEffect(() => {
    console.log('ログイン中のuser_id:', user?.user_id)
    console.log('Usersテーブル検索結果:', userInfo)
    console.log('user_name:', userInfo?.user_name ?? user?.user_name)
  }, [user, userInfo])

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-600">ログインしてください</p>
      </div>
    )
  }

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
              {meetings.map((meeting) => (
                <div key={meeting.meeting_id} className="mb-4 last:mb-0">
                  <Link href={`/feedback/${meeting.meeting_id}`} className="block">
                    <div className="mb-2 pb-2 border-b hover:bg-slate-50 transition-colors p-2 rounded">
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-medium text-gray-900">
                            {meeting.title || '無題の会議'}
                          </h3>
                          <p className="text-sm text-gray-600">
                            {meeting.client_company_name && `${meeting.client_company_name} - `}
                            {meeting.client_contact_name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(meeting.meeting_datetime).toLocaleString('ja-JP')}
                          </p>
                        </div>
                        <div className="text-sm text-blue-600">
                          {meeting.user_name}
                        </div>
                      </div>
                    </div>
                  </Link>
                  <div className="pl-2">
                    <CommentsList meetingId={meeting.meeting_id} />
                  </div>
                </div>
              ))}
            </ScrollArea>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}


