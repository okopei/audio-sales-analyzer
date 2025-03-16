"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { uploadToAzureStorage } from "@/lib/utils/azure-storage"
import Link from "next/link"

export default function TestUploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<{ success: boolean; message: string; url?: string }>()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setUploadResult({ success: false, message: "ファイルを選択してください" })
      return
    }

    try {
      setUploading(true)
      setUploadResult(undefined)

      // ファイル名に現在時刻を追加して一意にする
      const timestamp = new Date().getTime()
      const fileName = `${timestamp}_${file.name}`

      console.log('アップロード処理開始:', fileName)

      // Azure Blob Storageにアップロード
      const url = await uploadToAzureStorage(file, fileName)

      console.log('アップロード成功:', url)

      setUploadResult({
        success: true,
        message: "ファイルのアップロードに成功しました",
        url
      })
    } catch (error) {
      console.error("アップロードエラー:", error)
      setUploadResult({
        success: false,
        message: `アップロードに失敗しました: ${error instanceof Error ? error.message : String(error)}`
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 p-4">
      <div className="max-w-md mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Azure Blob Storageテストアップロード</CardTitle>
            <CardDescription>
              音声ファイルをAzure Blob Storageにアップロードします
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium">
                音声ファイル（.wav, .mp3）
              </label>
              <input
                type="file"
                accept=".wav,.mp3"
                onChange={handleFileChange}
                className="w-full border border-gray-300 rounded p-2"
              />
            </div>

            <Button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="w-full"
            >
              {uploading ? "アップロード中..." : "アップロード"}
            </Button>

            {uploadResult && (
              <div
                className={`p-3 rounded ${
                  uploadResult.success ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                }`}
              >
                <p>{uploadResult.message}</p>
                {uploadResult.url && (
                  <p className="text-xs mt-2 break-all">URL: {uploadResult.url}</p>
                )}
              </div>
            )}

            <div className="mt-4">
              <Link href="/dashboard" className="text-blue-600 hover:underline text-sm">
                ダッシュボードに戻る
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 