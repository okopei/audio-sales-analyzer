"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ArrowLeft, Search, X } from "lucide-react"
import Link from "next/link"

// 仮のユーザータイプ設定（実際はログイン情報から取得）
const userType = "Manager" // または "Member"

export default function MeetingSearch() {
  // テスト用に多めのデータを用意
  const [searchResults, setSearchResults] = useState([
    {
      id: 1,
      company: "株式会社ABC",
      industry: "IT・通信業",
      size: "大企業",
      date: "2024/01/15",
      status: "成約済",
      salesPerson: "田中 一郎",
      nextAction: "契約書の締結",
    },
    {
      id: 2,
      company: "株式会社XYZ",
      industry: "製造業",
      size: "中堅企業",
      date: "2024/01/10",
      status: "商談中",
      salesPerson: "鈴木 花子",
      nextAction: "見積書の提出",
    },
    {
      id: 3,
      company: "株式会社DEF",
      industry: "小売業",
      size: "中小企業",
      date: "2024/01/05",
      status: "終了",
      salesPerson: "佐藤 健一",
      nextAction: "競合採用",
    },
    // スクロールのテスト用データ
    ...Array(10)
      .fill(null)
      .map((_, index) => ({
        id: index + 4,
        company: `テスト企業${index + 4}`,
        industry: "その他",
        size: "中小企業",
        date: "2024/01/01",
        status: "商談中",
        salesPerson: "営業担当者",
        nextAction: "フォローアップ",
      })),
  ])

  const dashboardLink = userType === "Manager" ? "/manager-dashboard" : "/dashboard"

  return (
    <div className="min-h-screen bg-zinc-50 p-3 sm:p-6">
      {/* ヘッダー */}
      <div className="mb-4 sm:mb-6">
        <Link href={dashboardLink}>
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
            {userType === "Manager" && (
              <div className="space-y-1 sm:space-y-2">
                <label className="text-xs sm:text-sm font-medium">営業担当者</label>
                <Select>
                  <SelectTrigger className="text-xs sm:text-sm">
                    <SelectValue placeholder="選択してください" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全て</SelectItem>
                    <SelectItem value="tanaka">田中 一郎</SelectItem>
                    <SelectItem value="suzuki">鈴木 花子</SelectItem>
                    <SelectItem value="sato">佐藤 健一</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-1 sm:space-y-2">
              <label className="text-xs sm:text-sm font-medium">期間</label>
              <div className="grid grid-cols-2 gap-2">
                <Input type="date" className="text-xs sm:text-sm" />
                <Input type="date" className="text-xs sm:text-sm" />
              </div>
            </div>

            <div className="pt-3 sm:pt-4 space-y-2">
              <Button className="w-full text-xs sm:text-sm">
                <Search className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                検索
              </Button>
              <Button variant="outline" className="w-full text-xs sm:text-sm">
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

          <ScrollArea className="h-[300px] sm:h-[calc(50vh-100px)]">
            <div className="space-y-3 sm:space-y-4 pr-4">
              {searchResults.map((result) => (
                <Link
                  key={result.id}
                  href={`/feedback#${result.id}`}
                  className="block border rounded-lg p-3 sm:p-4 hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-medium text-sm sm:text-base">{result.company}</div>
                      {userType === "Manager" && (
                        <div className="text-xs sm:text-sm text-gray-500">担当: {result.salesPerson}</div>
                      )}
                    </div>
                    <div className="text-xs sm:text-sm text-gray-500">{result.date}</div>
                  </div>
                </Link>
              ))}
            </div>
          </ScrollArea>
        </Card>
      </div>
    </div>
  )
}

