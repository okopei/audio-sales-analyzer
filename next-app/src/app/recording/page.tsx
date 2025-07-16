"use client"
import { useState, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"
import { useRecording } from "@/hooks/useRecording"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Mic, Square } from "lucide-react"

// 録音ページのメインコンポーネント
function RecordingPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user } = useAuth()
  
  // URLパラメータからmeeting_idとuser_idを取得
  const meetingId = searchParams.get("meetingId")
  const userId = searchParams.get("userId")
  
  // ファイル名生成の共通関数
  const formatTimestamp = (date: Date): string => {
    return date.toISOString().replace(/:/g, '-').replace(/\..+/, match =>
      `-${match.slice(1, -1)}`
    )
  }
  
  const generateFileName = (meetingId: string | null, userId: string | null, extension: string = '.webm'): string => {
    const timestamp = formatTimestamp(new Date())
    
    if (meetingId && userId) {
      return `meeting_${meetingId}_user_${userId}_${timestamp}${extension}`
    } else if (userId) {
      return `recording_user_${userId}_${timestamp}${extension}`
    } else {
      return `recording_${timestamp}${extension}`
    }
  }
  
  // useRecordingフックを使用
  const {
    isRecording,
    recordingTime,
    formatTime,
    startRecording,
    stopRecording,
    getRecordingBlob,
    audioLevel,
    testMicrophone,
    uploadStatus,
    isUploading,
    processingStatus,
    sendAudioToServer
  } = useRecording(meetingId || undefined, userId || undefined)







  // 音声レベルを可視化するコンポーネント
  const AudioLevelVisualizer = () => (
    <div className="flex items-center gap-1 h-8">
      {audioLevel.map((level, index) => (
        <div
          key={index}
          className="w-1 bg-blue-500 rounded-full transition-all duration-100"
          style={{
            height: `${Math.max(2, level / 2)}px`,
            opacity: level > 0 ? 0.8 : 0.3
          }}
        />
      ))}
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
      <div className="flex flex-col items-center justify-center py-10 w-full max-w-md">

        
        {/* 録音機能セクション */}
        <Card className="w-full p-6 mb-4">
          <h2 className="text-lg font-semibold text-center mb-4">録音機能</h2>
          
          {/* 録音時間表示 */}
          <div className="text-center mb-4">
            <div className="text-2xl font-mono text-gray-700">
              {formatTime(recordingTime)}
            </div>
          </div>
          
          {/* 音声レベル表示 */}
          {isRecording && (
            <div className="mb-4">
              <AudioLevelVisualizer />
            </div>
          )}
          
          {/* 録音ボタン */}
          <div className="flex justify-center gap-4 mb-4">
            <Button
              onClick={isRecording ? stopRecording : startRecording}
              variant={isRecording ? "destructive" : "default"}
              size="lg"
              disabled={isUploading}
              className="flex items-center gap-2"
            >
              {isRecording ? (
                <>
                  <Square className="w-5 h-5" />
                  録音停止
                </>
              ) : (
                <>
                  <Mic className="w-5 h-5" />
                  録音開始
                </>
              )}
            </Button>
          </div>
          

        </Card>



        {/* ステータス表示 */}
        {uploadStatus && (
          <div className={`mt-2 p-3 border rounded-md text-sm w-full text-center ${
            uploadStatus.success ? 'bg-green-50 border-green-200 text-green-600' :
            'bg-red-50 border-red-200 text-red-600'
          }`}>
            <p>{uploadStatus.success ? 'アップロード完了' : `アップロード失敗: ${uploadStatus.error}`}</p>
            {uploadStatus.url && (
              <p className="text-xs mt-2 break-all">URL: {uploadStatus.url}</p>
            )}
          </div>
        )}
        
        {/* 処理状況表示 */}
        {processingStatus && (
          <div className="mt-2 p-3 border border-blue-200 rounded-md text-sm w-full text-center bg-blue-50 text-blue-600">
            <p>{processingStatus}</p>
          </div>
        )}

        <Button
          className="mt-8"
          variant="outline"
          onClick={() => router.push("/dashboard")}
        >
          ダッシュボードに戻る
        </Button>
      </div>
    </div>
  )
}

// Suspenseでラップした録音ページ
export default function RecordingPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
        <div className="flex flex-col items-center justify-center py-10 w-full max-w-md">
          <div className="text-center">
            <p>読み込み中...</p>
          </div>
        </div>
      </div>
    }>
      <RecordingPageContent />
    </Suspense>
  )
}