"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dot, Pause, Play, ArrowLeft } from "lucide-react"
import { useRouter } from "next/navigation"
import { useRecording } from "@/hooks/useRecording"
import { toast } from "sonner"
import { useEffect } from "react"
import Link from "next/link"

export default function RecordingPage() {
  const router = useRouter()
  const {
    isRecording,
    isPaused,
    stopRecording,
    pauseRecording,
    resumeRecording,
    setIsRecording,
    recordingTime,
    formatTime,
  } = useRecording()

  useEffect(() => {
    setIsRecording(true)
  }, [setIsRecording])

  const handleStop = async () => {
    stopRecording()
    toast.success("正常に録音が終了しました")
    router.push("/dashboard")
  }

  const handlePauseResume = () => {
    if (isPaused) {
      resumeRecording()
    } else {
      pauseRecording()
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="max-w-3xl mx-auto p-4">
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="outline" size="sm" className="text-xs">
                <ArrowLeft className="w-4 h-4 mr-2" />
                戻る
              </Button>
            </Link>
            <h1 className="text-lg font-semibold whitespace-nowrap">商談録音</h1>
          </div>
        </div>

        <div className="mb-4 flex justify-between items-center">
          <div className="flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1.5">
            <Dot
              className={`h-5 w-5 ${isPaused ? "" : "animate-pulse"} ${isPaused ? "text-amber-500" : "text-rose-500"}`}
            />
            <span className="text-xs font-medium">{isPaused ? "一時停止中" : "録音中"}</span>
            <span className="text-xs text-zinc-500">{formatTime(recordingTime)}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handlePauseResume} className="text-xs">
              {isPaused ? <Play className="h-4 w-4 mr-2" /> : <Pause className="h-4 w-4 mr-2" />}
              {isPaused ? "再開" : "一時停止"}
            </Button>
            <Button variant="destructive" size="sm" onClick={handleStop} className="text-xs">
              終了
            </Button>
          </div>
        </div>

        <Card className="h-[calc(100vh-220px)] sm:h-[calc(60vh-48px)]">
          <CardHeader className="border-b py-3">
            <CardTitle className="text-base">会話ログ</CardTitle>
          </CardHeader>
          <CardContent className="p-0 h-[calc(100%-57px)]">
            <div className="mb-4 rounded-lg bg-zinc-100 p-4 mx-4 mt-4">
              <div className="h-24 w-full">
                <svg className="h-full w-full" viewBox="0 0 400 100" preserveAspectRatio="none">
                  <path
                    d="M 0 50 Q 50 20, 100 50 T 200 50 T 300 50 T 400 50"
                    fill="none"
                    stroke="rgb(244, 114, 182)"
                    strokeWidth="2"
                  />
                </svg>
              </div>
            </div>

            <div className="space-y-4 px-4 pb-6 overflow-y-auto h-[calc(100%-180px)] sm:h-[calc(100%-200px)] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-zinc-200 [&::-webkit-scrollbar-track]:bg-transparent">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm text-zinc-500">
                  <span>13:30:15</span>
                  <span className="font-medium text-pink-600">営業担当</span>
                </div>
                <p className="text-sm">本日は、お時間をいただきありがとうございます。</p>
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm text-zinc-500">
                  <span>13:30:45</span>
                  <span className="font-medium text-blue-600">顧客</span>
                </div>
                <p className="text-sm">こちらこそ、よろしくお願いします。</p>
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm text-zinc-500">
                  <span>13:31:00</span>
                  <span className="font-medium text-pink-600">営業担当</span>
                </div>
                <p className="text-sm">まずは、現在の課題についてお伺いできればと...</p>
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm text-zinc-500">
                  <span>13:31:30</span>
                  <span className="font-medium text-blue-600">顧客</span>
                </div>
                <p className="text-sm">現在、主に3つの課題を抱えています。1つ目は...</p>
              </div>

              {/* スクロールのテスト用にダミーデータを追加 */}
              {Array.from({ length: 10 }).map((_, index) => (
                <div key={index} className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-zinc-500">
                    <span>13:32:{index.toString().padStart(2, "0")}</span>
                    <span className="font-medium text-pink-600">営業担当</span>
                  </div>
                  <p className="text-sm">会話内容のサンプルテキストです。スクロール機能の確認用に表示しています。</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

