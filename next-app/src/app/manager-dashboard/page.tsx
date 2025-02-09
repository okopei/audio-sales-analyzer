"use client"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Search } from "lucide-react"
import Link from "next/link"
import { ScrollArea } from "@/components/ui/scroll-area"

export default function ManagerDashboard() {
  const meetings = [
    {
      id: 1,
      staff: "田中 一郎",
      datetime: "02-07 14:00",
      client: "株式会社ABC",
      comment: "予算について具体的な話し合いができました。次回は見積書を持参します。",
      commentTime: "02-07 15:30",
      status: "未読",
    },
    {
      id: 2,
      staff: "鈴木 花子",
      datetime: "02-07 11:30",
      client: "DEF工業",
      comment: "技術的な課題について深い議論ができました。開発チームに確認が必要です。",
      commentTime: "02-07 13:00",
      status: "既読",
    },
    {
      id: 3,
      staff: "佐藤 健一",
      datetime: "02-06 15:00",
      client: "GHIシステムズ",
      comment: "導入に前向きな反応でした。来週までに提案書を準備します。",
      commentTime: "02-06 16:30",
      status: "未読",
    },
    // スクロールをテストするために追加のダミーデータ
    ...Array(10)
      .fill(null)
      .map((_, index) => ({
        id: index + 4,
        staff: `営業担当 ${index + 4}`,
        datetime: "02-05 10:00",
        client: `顧客 ${index + 4}`,
        comment: "これはテスト用のコメントです。",
        commentTime: "02-05 11:00",
        status: index % 2 === 0 ? "未読" : "既読",
      })),
  ]

  return (
    <div className="min-h-screen bg-zinc-50 p-4 sm:p-6">
      {/* ヘッダー */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Manager Dashboard: 山田 太郎</h1>
        <Link href="/meeting-search">
          <Button variant="outline" size="sm" className="text-sm">
            <Search className="w-4 h-4 mr-2" />
            商談検索
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 面談一覧 */}
        <Card className="p-4 sm:p-6">
          <h2 className="text-lg sm:text-xl font-semibold mb-4">面談一覧</h2>
          <ScrollArea className="h-[300px] sm:h-[600px]">
            <table className="w-full">
              <thead>
                <tr className="border-b text-sm">
                  <th className="text-left pb-2">営業担当</th>
                  <th className="text-left pb-2">日時</th>
                  <th className="text-left pb-2">顧客名</th>
                </tr>
              </thead>
              <tbody>
                {meetings.map((meeting) => (
                  <tr key={meeting.id} className="border-b last:border-0">
                    <td className="py-3">{meeting.staff}</td>
                    <td className="py-3">{meeting.datetime}</td>
                    <td className="py-3">{meeting.client}</td>
                  </tr>
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
              {meetings.map((meeting) => (
                <div key={meeting.id} className="border-b last:border-0 pb-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <div className="font-medium">{meeting.staff}</div>
                      <div className="text-sm text-gray-500">{meeting.client}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={meeting.status === "未読" ? "destructive" : "secondary"}>{meeting.status}</Badge>
                      <span className="text-sm text-gray-500">{meeting.commentTime}</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">{meeting.comment}</p>
                </div>
              ))}
            </div>
          </ScrollArea>
        </Card>
      </div>
    </div>
  )
}

