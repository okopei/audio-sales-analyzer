'use client'

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dot, Pause, Play } from "lucide-react"
import { useRouter } from 'next/navigation'
import { useRecording } from '@/hooks/useRecording'
import { toast } from 'sonner'
import { useEffect } from 'react'

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
    formatTime 
  } = useRecording()

  useEffect(() => {
    // ページロード時に録音状態を設定
    setIsRecording(true)
  }, [])

  const handleStop = async () => {
    stopRecording()
    toast.success('正常に録音が終了しました')
    router.push('/dashboard')
  }

  const handlePauseResume = () => {
    if (isPaused) {
      resumeRecording()
    } else {
      pauseRecording()
    }
  }

  return (
    <div className="min-h-screen bg-[#1F1F1F]">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-medium text-white">商談録音</h1>
            <div className="flex items-center gap-2 rounded-full bg-zinc-800 px-3 py-1.5">
              <Dot className={`h-5 w-5 ${isPaused ? '' : 'animate-pulse'} ${isPaused ? 'text-amber-500' : 'text-rose-500'}`} />
              <span className="text-sm font-medium text-white">
                {isPaused ? '一時停止中' : '録音中'}
              </span>
              <span className="text-sm text-zinc-400">{formatTime(recordingTime)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              className="border-zinc-700 bg-amber-500 text-white hover:bg-amber-600 transition-colors"
              onClick={handlePauseResume}
            >
              {isPaused ? (
                <Play className="h-4 w-4 mr-2" />
              ) : (
                <Pause className="h-4 w-4 mr-2" />
              )}
              {isPaused ? '再開' : '一時停止'}
            </Button>
            <Button 
              variant="default" 
              className="bg-rose-500 text-white hover:bg-rose-600 transition-colors"
              onClick={handleStop}
            >
              終了
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="border-zinc-800 bg-[#1F1F1F] text-white">
            <CardHeader>
              <CardTitle className="text-zinc-200">会話ログ</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4 rounded-lg bg-zinc-900 p-4">
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

              <div className="space-y-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <span>13:30:15</span>
                    <span className="font-medium text-pink-400">営業担当</span>
                  </div>
                  <p className="text-sm text-zinc-100">本日は、お時間をいただきありがとうございます。</p>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <span>13:30:45</span>
                    <span className="font-medium text-blue-400">顧客</span>
                  </div>
                  <p className="text-sm text-zinc-100">こちらこそ、よろしくお願いします。</p>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <span>13:31:00</span>
                    <span className="font-medium text-pink-400">営業担当</span>
                  </div>
                  <p className="text-sm text-zinc-100">まずは、現在の課題についてお伺いできればと...</p>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <span>13:31:30</span>
                    <span className="font-medium text-blue-400">顧客</span>
                  </div>
                  <p className="text-sm text-zinc-100">現在、主に3つの課題を抱えています。1つ目は...</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-[#1F1F1F] text-white">
            <CardHeader>
              <CardTitle className="text-zinc-200">営業計画</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="mb-2 text-sm font-medium text-zinc-400">ゴール</h3>
                <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
                  <p className="text-sm text-zinc-300">課題の深掘りと解決策の提案、次回アポイントの獲得</p>
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium text-zinc-400">アジェンダ</h3>
                <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
                  <ul className="list-inside list-disc space-y-1 text-sm text-zinc-300">
                    <li>現状の課題ヒアリング</li>
                    <li>解決策の提案</li>
                    <li>質疑応答</li>
                    <li>次回アポイントの調整</li>
                  </ul>
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium text-zinc-400">注意点</h3>
                <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
                  <ul className="list-inside list-disc space-y-1 text-sm text-zinc-300">
                    <li>予算に関する具体的な話は次回以降に</li>
                    <li>競合製品の導入検討状況を確認</li>
                  </ul>
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium text-zinc-400">使える事例</h3>
                <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
                  <ul className="list-inside list-disc space-y-1 text-sm text-zinc-300">
                    <li>A社様での導入効果</li>
                    <li>B社様での運用方法</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

