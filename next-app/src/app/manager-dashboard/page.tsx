"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Search, PlusCircle } from "lucide-react"
import Link from "next/link"
import { ScrollArea } from "@/components/ui/scroll-area"

export default function ManagerDashboard() {
  const meetings = [
    {
      id: 1,
      datetime: "02-07 14:00",
      client: "株式会社ABC",
      salesPerson: "田中 一郎",
    },
    {
      id: 2,
      datetime: "02-07 11:30",
      client: "DEF工業",
      salesPerson: "鈴木 花子",
    },
    {
      id: 3,
      datetime: "02-06 15:00",
      client: "GHIシステムズ",
      salesPerson: "佐藤 健一",
    },
    // スクロールをテストするために追加のダミーデータ
    ...Array(10)
      .fill(null)
      .map((_, index) => ({
        id: index + 4,
        datetime: "02-05 10:00",
        client: `顧客 ${index + 4}`,
        salesPerson: "山田 太郎",
      })),
  ]

  const comments = [
    {
      id: 1,
      client: "株式会社ABC",
      comment: "予算について具体的な話し合いができました。次回は見積書を持参します。",
      commentTime: "02-07 15:30",
      salesPerson: "田中 一郎",
      isRead: false,
    },
    {
      id: 2,
      client: "DEF工業",
      comment: "技術的な課題について深い議論ができました。開発チームに確認が必要です。",
      commentTime: "02-07 13:00",
      salesPerson: "鈴木 花子",
      isRead: true,
    },
    {
      id: 3,
      client: "GHIシステムズ",
      comment: "導入に前向きな反応でした。来週までに提案書を準備します。",
      commentTime: "02-06 16:30",
      salesPerson: "佐藤 健一",
      isRead: false,
    },
    // スクロールをテストするために追加のダミーデータ
    ...Array(10)
      .fill(null)
      .map((_, index) => ({
        id: index + 4,
        client: `顧客 ${index + 4}`,
        comment: "これはテスト用のコメントです。",
        commentTime: "02-05 11:00",
        salesPerson: "山田 太郎",
        isRead: index % 2 === 0,
      })),
  ]

  // 現在の日付を取得
  const today = new Date()
  const dateStr = today.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })

  return (
    <div className="min-h-screen bg-zinc-50 p-4 sm:p-6">
      {/* ヘッダー */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div className="text-xl font-medium">{dateStr}</div>
        <div className="flex items-center gap-2 sm:mx-auto">
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
        </div>
        <div className="text-xl font-medium">管理者</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 面談一覧 */}
        <Card className="p-4 sm:p-6">
          <h2 className="text-lg sm:text-xl font-semibold mb-4">過去商談一覧</h2>
          <ScrollArea className="h-[300px] sm:h-[600px]">
            <table className="w-full">
              <thead>
                <tr className="border-b text-sm">
                  <th className="text-left pb-2">担当者</th>
                  <th className="text-left pb-2">日時</th>
                  <th className="text-left pb-2">顧客名</th>
                </tr>
              </thead>
              <tbody>
                {meetings.map((meeting) => (
                  <Link
                    key={meeting.id}
                    href={`/feedback#${meeting.id}`}
                    className="table-row border-b last:border-0 hover:bg-slate-50 transition-colors"
                  >
                    <td className="py-3">{meeting.salesPerson}</td>
                    <td className="py-3">{meeting.datetime}</td>
                    <td className="py-3">{meeting.client}</td>
                  </Link>
                ))}
              </tbody>
            </table>
          </ScrollArea>
        </Card>

        {/* 最新のコメント */}
        <Card className="p-4 sm:p-6">
          <h2 className="text-lg sm:text-xl font-semibold mb-4">最新のコメント</h2>
          <ScrollArea className="h-[300px] sm:h-[600px]">
            <div className="space-y-4">
              {comments.map((comment) => (
                <Link
                  key={comment.id}
                  href={`/feedback#${comment.id}`}
                  className="block border-b last:border-0 pb-4 hover:bg-slate-50 rounded-lg transition-colors"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <div className="text-sm font-medium">{comment.salesPerson}</div>
                      <div className="text-sm text-gray-500">{comment.client}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {!comment.isRead && <Badge variant="destructive">未読</Badge>}
                      <span className="text-sm text-gray-500">{comment.commentTime}</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">{comment.comment}</p>
                </Link>
              ))}
            </div>
          </ScrollArea>
        </Card>
      </div>
    </div>
  )
}


