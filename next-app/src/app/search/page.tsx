"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ArrowLeft, Search, X } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Meeting, User, MeetingSearchParams } from "@/types/meeting"
import { searchMeetings } from "@/lib/api/meetings"
import { getUsers } from "@/lib/api/users"

// ユーザータイプの定数
const USER_TYPES = {
  MANAGER: "Manager",
  MEMBER: "Member",
} as const

export default function MeetingSearch() {
  const router = useRouter()
  const [selectedUserId, setSelectedUserId] = useState<string>("all")
  const [fromDate, setFromDate] = useState<string>("")
  const [toDate, setToDate] = useState<string>("")
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ユーザー一覧の取得と監視
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const usersData = await getUsers()
        console.log("取得したユーザー一覧:", usersData)
        setUsers(usersData)
      } catch (err) {
        console.error("ユーザー一覧の取得に失敗しました:", err)
        setError("ユーザー一覧の取得に失敗しました")
      }
    }
    fetchUsers()
  }, [])

  // usersの状態変更を監視
  useEffect(() => {
    if (users.length > 0) {
      console.log("描画時の users:", users)
    }
  }, [users])

  const fetchMeetings = async (params?: MeetingSearchParams) => {
    try {
      setIsLoading(true)
      setError(null)
      console.log("🧾 fetchMeetings 呼び出しパラメータ:", params)
      
      const response = await searchMeetings({
        ...params,
        userId: params?.userId || undefined
      })
      
      console.log("✅ searchMeetings 成功:", response)
      // 配列であることを確認してから設定
      setMeetings(Array.isArray(response) ? response : [])
      
    } catch (err) {
      console.error("❌ searchMeetings エラー:", err)
      setError("データの取得に失敗しました")
      console.error(err)
      setMeetings([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = () => {
    const params: MeetingSearchParams = {}
    if (selectedUserId && selectedUserId !== "all") {
      params.userId = selectedUserId
    }
    if (fromDate) params.fromDate = fromDate
    if (toDate) params.toDate = toDate
    fetchMeetings(params)
  }

  const handleClear = () => {
    setSelectedUserId("all")
    setFromDate("")
    setToDate("")
  }

  return (
    <div className="min-h-screen bg-zinc-50 p-3 sm:p-6">
      {/* ヘッダー */}
      <div className="mb-4 sm:mb-6">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm" className="mb-2 sm:mb-4 text-xs sm:text-sm">
            <ArrowLeft className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
            ダッシュボードに戻る
          </Button>
        </Link>
        <h1 className="text-xl sm:text-2xl font-bold">過去面談検索</h1>
      </div>

      <div className="grid gap-4 sm:gap-6 md:grid-cols-[350px,1fr]">
        {/* 検索条件 */}
        <Card className="p-4 sm:p-6 bg-white shadow-md">
          <h2 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4">検索条件</h2>
          <div className="space-y-3 sm:space-y-4">
            <div className="space-y-1 sm:space-y-2">
              <label className="text-xs sm:text-sm font-medium">営業担当者</label>
              <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                <SelectTrigger className="text-xs sm:text-sm truncate">
                  <SelectValue placeholder="選択してください" />
                </SelectTrigger>
                <SelectContent>
                  <ScrollArea className="h-60">
                    <SelectItem key="all" value="all">全て</SelectItem>
                    {users
                      .filter((user) => user.user_id && user.user_name)
                      .map((user) => (
                        <SelectItem key={`user-${user.user_id}`} value={String(user.user_id)}>
                          {user.user_name}
                        </SelectItem>
                      ))}
                  </ScrollArea>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1 sm:space-y-2">
              <label className="text-xs sm:text-sm font-medium">期間</label>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="date"
                  className="text-xs sm:text-sm"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                />
                <Input
                  type="date"
                  className="text-xs sm:text-sm"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                />
              </div>
            </div>

            <div className="pt-3 sm:pt-4 space-y-2">
              <Button
                className="w-full text-xs sm:text-sm"
                onClick={handleSearch}
                disabled={isLoading}
              >
                <Search className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                検索
              </Button>
              <Button
                variant="outline"
                className="w-full text-xs sm:text-sm"
                onClick={handleClear}
                disabled={isLoading}
              >
                <X className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                条件をクリア
              </Button>
            </div>
          </div>
        </Card>

        {/* 検索結果 */}
        <Card className="p-4 sm:p-6 bg-white shadow-sm">
          <div className="flex justify-between items-center mb-3 sm:mb-4">
            <h2 className="text-base sm:text-lg font-semibold">検索結果</h2>
            <Select defaultValue="date-desc">
              <SelectTrigger className="w-[140px] sm:w-[180px] text-xs sm:text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date-desc">日付（新しい順）</SelectItem>
                <SelectItem value="date-asc">日付（古い順）</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {error && (
            <div className="text-red-500 text-sm mb-4">{error}</div>
          )}

          <ScrollArea className="h-[300px] sm:h-[calc(50vh-100px)]">
            <div className="space-y-3 sm:space-y-4 pr-4">
              {meetings.map((meeting) => (
                <Link
                  key={meeting.meeting_id}
                  href={`/feedback#${meeting.meeting_id}`}
                  className="block border rounded-lg p-3 sm:p-4 hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-medium text-sm sm:text-base">
                        {meeting.client_company_name}
                      </div>
                      <div className="text-xs sm:text-sm text-gray-500">
                        担当: {users.find(u => String(u.user_id) === String(meeting.user_id))?.user_name || "不明"}
                      </div>
                      <div className="text-xs sm:text-sm text-gray-500">
                        連絡先: {meeting.client_contact_name}
                      </div>
                      <div className="text-xs sm:text-sm text-gray-500">
                        状態: {meeting.status}
                      </div>
                    </div>
                    <div className="text-xs sm:text-sm text-gray-500">
                      {new Date(meeting.meeting_datetime).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" })}
                    </div>
                  </div>
                </Link>
              ))}
              {meetings.length === 0 && !isLoading && !error && (
                <div className="text-center text-gray-500 py-4">検索結果がありません</div>
              )}
              {isLoading && (
                <div className="text-center text-gray-500 py-4">読み込み中...</div>
              )}
            </div>
          </ScrollArea>
        </Card>
      </div>
    </div>
  )
}

