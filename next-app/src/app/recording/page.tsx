"use client"
import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"
import { uploadToAzureStorage } from "@/lib/utils/azure-storage"
import { useDropzone } from "react-dropzone"

export default function RecordingPage() {
  const router = useRouter()
  const { user } = useAuth()
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<{
    success?: boolean
    message?: string
    url?: string
  } | null>(null)

  const handleFileUpload = async (file: File) => {
    if (!user) {
      setUploadStatus({ success: false, message: "ログインしてください" })
      return
    }
    try {
      setIsUploading(true)
      setUploadStatus({ message: "音声をアップロード中..." })
      const userId = user.user_id
      const now = new Date()
      const timestamp = now.toISOString().replace(/[:.]/g, '-')
      const fileName = `recording_user_${userId}_${timestamp}${file.name.substring(file.name.lastIndexOf('.'))}`
      const blobUrl = await uploadToAzureStorage(file, fileName)
      setUploadStatus({
        success: true,
        message: "音声のアップロードに成功しました。ダッシュボードに移動します...",
        url: blobUrl
      })
      setTimeout(() => {
        if (user?.account_status === 'ACTIVE' && user?.is_manager) {
          router.push('/manager-dashboard')
        } else {
          router.push('/dashboard')
        }
      }, 2000)
    } catch (error) {
      setUploadStatus({ success: false, message: "アップロードに失敗しました" })
    } finally {
      setIsUploading(false)
    }
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles[0]) handleFileUpload(acceptedFiles[0])
  }, [user])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "audio/*": [".mp3", ".m4a", ".wav"] },
    multiple: false,
  })

  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
      <div className="flex flex-col items-center justify-center py-10 w-full max-w-md">
        <img
          src="/under_construction.png"
          alt="工事中"
          className="w-64 h-auto opacity-90 mb-6"
        />
        <div {...getRootProps()} className="w-full border-2 border-dashed border-blue-300 rounded-lg p-6 text-center cursor-pointer bg-white hover:bg-blue-50 transition mb-4">
          <input {...getInputProps()} />
          {isDragActive ? (
            <p className="text-blue-600">ここに音声ファイルをドロップしてください</p>
          ) : (
            <>
              <p className="text-gray-700 font-medium">音声ファイルをアップロード</p>
              <p className="text-xs text-gray-500 mt-1">対応形式: mp3, m4a, wav</p>
              <button
                type="button"
                className="mt-4 px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition"
                disabled={isUploading}
              >
                ファイルを選択
              </button>
            </>
          )}
        </div>
        {uploadStatus && (
          <div className={`mt-2 p-3 border rounded-md text-sm w-full text-center ${
            uploadStatus.success === undefined ? 'bg-blue-50 border-blue-200 text-blue-600' :
            uploadStatus.success ? 'bg-green-50 border-green-200 text-green-600' :
            'bg-red-50 border-red-200 text-red-600'
          }`}>
            <p>{uploadStatus.message}</p>
            {uploadStatus.url && (
              <p className="text-xs mt-2 break-all">URL: {uploadStatus.url}</p>
            )}
          </div>
        )}
        <button
          className="mt-8 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          onClick={() => router.push("/dashboard")}
        >
          ダッシュボードに戻る
        </button>
      </div>
    </div>
  )
}