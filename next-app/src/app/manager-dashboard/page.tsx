"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

// 仮のデータ
const meetings = [
  {
    id: 1,
    salesPerson: "田中 一郎",
    date: "02-07 14:00",
    customer: "株式会社ABC",
    url: "#",
  },
  {
    id: 2,
    salesPerson: "鈴木 花子",
    date: "02-07 11:30",
    customer: "DEF工業",
    url: "#",
  },
  {
    id: 3,
    salesPerson: "佐藤 健一",
    date: "02-06 15:00",
    customer: "GHIシステムズ",
    url: "#",
  },
]

const comments = [
  {
    id: 1,
    salesPerson: "田中 一郎",
    date: "02-07 15:30",
    customer: "株式会社ABC",
    comment: "予算について具体的な話し合いができました。次回は見積書を持参します。",
    url: "#",
    isRead: false,
  },
  {
    id: 2,
    salesPerson: "鈴木 花子",
    date: "02-07 13:00",
    customer: "DEF工業",
    comment: "技術的な課題について深い議論ができました。開発チームに確認が必要です。",
    url: "#",
    isRead: true,
  },
  {
    id: 3,
    salesPerson: "佐藤 健一",
    date: "02-06 16:30",
    customer: "GHIシステムズ",
    comment: "導入に前向きな反応でした。来週までに提案書を準備します。",
    url: "#",
    isRead: false,
  },
]

export default function ManagerDashboard() {
  // 現在の日付を取得
  const today = new Date()
  const dateStr = today.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })

  return (
    <div className="min-h-screen bg-white p-4">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* ヘッダー */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-xl font-medium">{dateStr}</h1>
          <div className="text-xl font-medium">山田 太郎 様</div>
        </div>

        {/* メインコンテンツ */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* 面談一覧 */}
          <Card>
            <CardHeader>
              <CardTitle>面談一覧</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>営業担当</TableHead>
                      <TableHead>日時</TableHead>
                      <TableHead>顧客名</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {meetings.map((meeting) => (
                      <TableRow
                        key={meeting.id}
                        className="cursor-pointer hover:bg-slate-100"
                        onClick={() => (window.location.href = meeting.url)}
                      >
                        <TableCell>{meeting.salesPerson}</TableCell>
                        <TableCell>{meeting.date}</TableCell>
                        <TableCell>{meeting.customer}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* 最新のコメント */}
          <Card>
            <CardHeader>
              <CardTitle>最新のコメント</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px]">
                <div className="space-y-4">
                  {comments.map((comment) => (
                    <div
                      key={comment.id}
                      onClick={() => (window.location.href = comment.url)}
                      className="p-4 rounded border cursor-pointer hover:bg-slate-100"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="font-medium">{comment.salesPerson}</div>
                        <div className="flex items-center gap-2">
                          <Badge variant={comment.isRead ? "secondary" : "destructive"}>
                            {comment.isRead ? "既読" : "未読"}
                          </Badge>
                          <div className="text-sm text-gray-500">{comment.date}</div>
                        </div>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">{comment.customer}</div>
                      <div className="text-sm">{comment.comment}</div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

