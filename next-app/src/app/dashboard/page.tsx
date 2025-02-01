import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { CalendarClock, Plus, Search } from "lucide-react"

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#1F1F1F]">
      <header className="flex h-14 items-center justify-between border-b border-zinc-800 bg-[#1F1F1F] px-6">
        <h1 className="text-lg font-medium text-white">マイダッシュボード</h1>
        <Avatar>
          <AvatarImage src="/placeholder-user.jpg" />
          <AvatarFallback>鈴木</AvatarFallback>
        </Avatar>
      </header>

      <div className="p-6">
        <div className="mb-8">
          <h2 className="mb-4 text-lg font-medium text-white">今月の進捗状況</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex flex-col items-center">
              <div className="relative flex h-32 w-32 items-center justify-center rounded-full border-4 border-pink-500/20">
                <div
                  className="absolute -right-1 -top-1 h-32 w-32 rounded-full border-4 border-pink-500 border-t-transparent"
                  style={{ transform: "rotate(252deg)" }}
                ></div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">70%</div>
                  <div className="text-sm text-zinc-400">14/20件</div>
                </div>
              </div>
              <div className="mt-2 text-center text-sm text-zinc-200">商談実施件数</div>
            </div>

            <div className="flex flex-col items-center">
              <div className="relative flex h-32 w-32 items-center justify-center rounded-full border-4 border-pink-500/20">
                <div
                  className="absolute -right-1 -top-1 h-32 w-32 rounded-full border-4 border-pink-500 border-t-transparent"
                  style={{ transform: "rotate(234deg)" }}
                ></div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">65%</div>
                  <div className="text-sm text-zinc-400">13/20件</div>
                </div>
              </div>
              <div className="mt-2 text-center text-sm text-zinc-200">成約件数</div>
            </div>

            <div className="flex flex-col items-center">
              <div className="relative flex h-32 w-32 items-center justify-center rounded-full border-4 border-pink-500/20">
                <div
                  className="absolute -right-1 -top-1 h-32 w-32 rounded-full border-4 border-pink-500 border-t-transparent"
                  style={{ transform: "rotate(288deg)" }}
                ></div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">80%</div>
                  <div className="text-sm text-zinc-400">4.0/5.0M</div>
                </div>
              </div>
              <div className="mt-2 text-center text-sm text-zinc-200">成約額</div>
            </div>
          </div>
        </div>

        <div className="mb-6">
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border-zinc-800 bg-[#1F1F1F] text-white">
              <CardHeader>
                <CardTitle className="text-zinc-200">本日の予定</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border border-zinc-800 bg-gradient-to-r from-pink-500/5 to-rose-500/5 p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-pink-500/20">
                      <CalendarClock className="h-4 w-4 text-pink-300" />
                    </div>
                    <div>
                      <div className="font-medium">10:00 - 株式会社ABC</div>
                      <div className="text-sm text-zinc-400">商談フェーズ: 提案フェーズ</div>
                    </div>
                  </div>
                </div>
                <div className="rounded-lg border border-zinc-800 bg-gradient-to-r from-rose-500/5 to-pink-500/5 p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-pink-500/20">
                      <CalendarClock className="h-4 w-4 text-pink-300" />
                    </div>
                    <div>
                      <div className="font-medium">14:00 - 株式会社XYZ</div>
                      <div className="text-sm text-zinc-400">商談フェーズ: クロージング</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-zinc-800 bg-[#1F1F1F] text-white">
              <CardHeader>
                <CardTitle className="text-zinc-200">商談ステータス一覧</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="border-zinc-800">
                      <TableHead className="text-zinc-400">顧客企業</TableHead>
                      <TableHead className="text-zinc-400">フェーズ</TableHead>
                      <TableHead className="text-zinc-400">最終接触</TableHead>
                      <TableHead className="text-zinc-400">Next Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow className="border-zinc-800">
                      <TableCell className="font-medium text-white">株式会社ABC</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center rounded-md bg-orange-400/10 px-2 py-1 text-xs font-medium text-orange-400 ring-1 ring-inset ring-orange-400/20">
                          提案フェーズ
                        </span>
                      </TableCell>
                      <TableCell className="text-zinc-400">2024/01/21</TableCell>
                      <TableCell className="text-zinc-400">見積提出</TableCell>
                    </TableRow>
                    <TableRow className="border-zinc-800">
                      <TableCell className="font-medium text-white">株式会社XYZ</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center rounded-md bg-emerald-400/10 px-2 py-1 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-400/20">
                          クロージング
                        </span>
                      </TableCell>
                      <TableCell className="text-zinc-400">2024/01/20</TableCell>
                      <TableCell className="text-zinc-400">契約締結</TableCell>
                    </TableRow>
                    <TableRow className="border-zinc-800">
                      <TableCell className="font-medium text-white">株式会社DEF</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center rounded-md bg-blue-400/10 px-2 py-1 text-xs font-medium text-blue-400 ring-1 ring-inset ring-blue-400/20">
                          初回面談
                        </span>
                      </TableCell>
                      <TableCell className="text-zinc-400">2024/01/19</TableCell>
                      <TableCell className="text-zinc-400">ヒアリング</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </div>

        <div>
          <h2 className="mb-4 text-lg font-medium text-white">クイックアクション</h2>
          <div className="flex gap-4">
            <Button className="flex-1 border-zinc-800 bg-[#1F1F1F] text-white hover:bg-zinc-800" variant="outline">
              <Plus className="mr-2 h-4 w-4" />
              新規商談を記録
            </Button>
            <Button className="flex-1 border-zinc-800 bg-[#1F1F1F] text-white hover:bg-zinc-800" variant="outline">
              <Search className="mr-2 h-4 w-4" />
              商談検索
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

