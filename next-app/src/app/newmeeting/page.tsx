"use client"

import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useRouter } from "next/navigation"
import { useRecording } from "@/hooks/useRecording"
import { Upload, Mic } from "lucide-react"
import { useDropzone } from "react-dropzone"
import { saveBasicInfo } from "@/lib/api-client"
import { useAuth } from "@/hooks/useAuth"
import ProtectedRoute from "@/components/auth/ProtectedRoute"
import { uploadToAzureStorage } from "@/lib/utils/azure-storage"
import { toast } from "react-hot-toast"

export default function NewMeetingPage() {
  const router = useRouter()
  const { startRecording } = useRecording()
  const { user } = useAuth()
  const [isMobile, setIsMobile] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<{
    success?: boolean
    message?: string
    url?: string
  } | null>(null)
  const [createdMeetingId, setCreatedMeetingId] = useState<number | null>(null)

  useEffect(() => {
    setIsMobile(/iPhone|iPad|iPod|Android/i.test(navigator.userAgent))
  }, [])

  // 現在時刻から1時間後（1時間刻みで四捨五入）の初期値を計算
  const getInitialDateTime = () => {
    const now = new Date()
    const roundedHour = Math.ceil(now.getHours() + 1)
    const initialDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), roundedHour, 0, 0)

    return {
      year: initialDate.getFullYear().toString(),
      month: (initialDate.getMonth() + 1).toString().padStart(2, "0"),
      day: initialDate.getDate().toString().padStart(2, "0"),
      hour: initialDate.getHours().toString().padStart(2, "0"),
    }
  }

  const [formData, setFormData] = useState({
    ...getInitialDateTime(),
    companyName: "",
    companyNameBiz: "",
    industry: "",
    scale: "",
    meetingGoal: "",
  })

  useEffect(() => {
    if (user?.user_name) {
      // contactPersonの更新処理を削除
    }
  }, [user])

  // 年の選択肢を生成（現在年から+1年まで）
  const getYearOptions = () => {
    const currentYear = new Date().getFullYear()
    return [currentYear, currentYear + 1]
  }

  // 月の選択肢を生成（1-12月）
  const getMonthOptions = () => {
    return Array.from({ length: 12 }, (_, i) => i + 1)
  }

  // 日の選択肢を生成（選択された年月に応じて）
  const getDayOptions = () => {
    const daysInMonth = new Date(Number.parseInt(formData.year), Number.parseInt(formData.month), 0).getDate()
    return Array.from({ length: daysInMonth }, (_, i) => i + 1)
  }

  // 時間の選択肢を生成（9:00-18:00）
  const getHourOptions = () => {
    return Array.from({ length: 10 }, (_, i) => i + 9)
  }

  // 基本情報を保存する関数
  const handleSubmit = async (type: "save" | "next"): Promise<number | null> => {
    if (!user) {
      toast.error("ログインしてください")
      return null
    }

    if (!formData.companyName) {
      toast.error("顧客名を入力してください")
      return null
    }

    if (!formData.companyNameBiz) {
      toast.error("企業名を入力してください")
      return null
    }

    try {
      setIsSubmitting(true)
      setSubmitError(null)

      // 会議日時文字列を作成
      const meeting_datetime = `${formData.year}-${formData.month.padStart(2, "0")}-${formData.day.padStart(2, "0")} ${formData.hour.padStart(2, "0")}:00:00`;
      
      // Save basic info
      const basicInfoData = {
        userId: user.user_id,
        year: formData.year,
        month: formData.month,
        day: formData.day,
        hour: formData.hour,
        companyName: formData.companyName,
        client_company_name: formData.companyNameBiz,
        client_contact_name: formData.companyName,
        industry: formData.industry,
        scale: formData.scale,
        meeting_goal: formData.meetingGoal,
        meeting_datetime: meeting_datetime,
      }

      console.log("Submitting form data:", basicInfoData);
      
      // API を呼び出して商談情報を保存（BasicInfoテーブルに保存）
      const response = await saveBasicInfo(basicInfoData)
      
      console.log("BasicInfo saved successfully:", response)
      
      // 会議IDの取得を確認
      if (!response.search_info?.meeting_id) {
        throw new Error("会議IDの取得に失敗しました")
      }
      
      // ☆の情報をローカルストレージに保存（録音画面での検索用）
      try {
        const basicMeetingInfo = {
          userId: user.user_id,
          client_company_name: formData.companyNameBiz,
          client_contact_name: formData.companyName,
          meeting_datetime: meeting_datetime
        };
        
        localStorage.setItem('basicMeetingInfo', JSON.stringify(basicMeetingInfo));
        
        // responseから検索情報を取得
        if (response.search_info) {
          console.log("検索情報をローカルストレージに保存:", response.search_info);
        }
        
        console.log("基本情報をローカルストレージに保存:", basicMeetingInfo);
      } catch (storageError) {
        console.warn("ローカルストレージへの保存に失敗:", storageError);
        // 処理は続行
      }
      
      // 成功時の処理
      if (type === "next") {
        // 会議IDの取得 - これは録音画面で検索される
        console.log("BasicInfo保存完了、検索情報:", response.search_info);
        
        // 商談情報の保存完了をトーストで通知
        toast.success("商談情報を保存しました。録音画面に移動します");
        
        // データベースへの反映を確実にするために少し待機
        setTimeout(() => {
          console.log("録音画面へ移動します");
          // 録音ページへ移動
          router.push(`/recording`);
        }, 1000);
      } else {
        // 保存成功メッセージを表示
        toast.success(`商談情報を保存しました: ${response.message}`);
        // 会議IDを返す
        return response.search_info.meeting_id;
      }
    } catch (error) {
      console.error("Error saving basic info:", error)
      
      // エラーメッセージの詳細を取得
      let errorMessage = "基本情報の保存に失敗しました";
      
      if (error instanceof Error) {
        errorMessage = error.message;
        
        // データベース接続エラーの特別な処理
        if (errorMessage.includes('データベース接続') || 
            errorMessage.includes('SQLDriverConnect') ||
            errorMessage.includes('ドライバー') ||
            errorMessage.includes('connection') ||
            errorMessage.includes('Failed to retrieve')) {
          errorMessage = "データベース接続エラーが発生しました。サーバー管理者に連絡してください。";
          toast.error("データベース接続エラー", {
            duration: 6000,
            icon: "🛑",
          });
          
          console.error("データベース接続エラーの詳細:", error.message);
        }
      }
      
      // エラーメッセージを設定
      setSubmitError(errorMessage);
      
      // モーダルやトーストでエラーを表示
      toast.error(`エラー: ${errorMessage}`);
    } finally {
      setIsSubmitting(false)
    }
    
    return null // エラー時はnullを返す
  }

  const handleFileUpload = async (file: File) => {
    if (!user) {
      toast.error("ログインしてください")
      return
    }
    
    try {
      setIsUploading(true)
      setUploadStatus({ message: "商談情報を保存しています..." })
      
      // 基本情報を保存して会議IDを取得
      const meetingId = await handleSubmit("save")
      
      if (!meetingId) {
        setUploadStatus({
          success: false,
          message: "商談情報の保存に失敗しました。もう一度お試しください。"
        })
        return
      }
      
      console.log("取得した会議ID:", meetingId)
      
      // 音声ファイルをWebM形式に変換（内部的に処理）
      const webmFile = await convertToWebM(file)
      
      setUploadStatus({ message: "音声をアップロード中..." })
      
      console.log("音声アップロード開始:", webmFile.name, "会議ID:", meetingId)
      
      // meeting_idとuser_idを含むファイル名を生成
      const userId = user.user_id
      const now = new Date()
      const timestamp = now.toISOString().replace(/[:.]/g, '-').replace('Z', '')
      const fileName = `meeting_${meetingId}_user_${userId}_${timestamp}.webm`
      
      console.log("アップロード用ファイル名:", fileName)
      
      // Azure Blob Storageにアップロード
      const blobUrl = await uploadToAzureStorage(webmFile, fileName)
      
      console.log("アップロード成功:", blobUrl)
      
      setUploadStatus({
        success: true,
        message: "音声のアップロードに成功しました。ダッシュボードに移動します...",
        url: blobUrl
      })
      
      // 成功メッセージ表示後、ダッシュボードに遷移
      setTimeout(() => {
        if (user?.account_status === 'ACTIVE' && user?.role === 'manager') {
          router.push('/manager-dashboard')
        } else {
          router.push('/dashboard')
        }
      }, 2000)
    } catch (error) {
      console.error("アップロードエラー:", error)
      let errorMessage = "アップロードに失敗しました"
      
      if (error instanceof Error) {
        if (error.message.includes("MediaRecorder")) {
          errorMessage = "音声ファイルの変換に失敗しました。別のファイルを試してください。"
        } else if (error.message.includes("BlobStorage")) {
          errorMessage = "ストレージへのアップロードに失敗しました。ネットワーク接続を確認してください。"
        }
      }
      
      setUploadStatus({
        success: false,
        message: errorMessage
      })
    } finally {
      setIsUploading(false)
    }
  }

  const convertToWebM = async (file: File): Promise<File> => {
    return new Promise((resolve, reject) => {
      try {
        // 音声ファイルを読み込む
        const reader = new FileReader()
        reader.onload = async (e) => {
          try {
            const arrayBuffer = e.target?.result as ArrayBuffer
            const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
            
            // 音声データをデコード
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
            
            // 音声データをMediaStreamに変換
            const destination = audioContext.createMediaStreamDestination()
            const source = audioContext.createBufferSource()
            source.buffer = audioBuffer
            source.connect(destination)
            
            // WebM形式でエンコード
            const mediaRecorder = new MediaRecorder(destination.stream, {
              mimeType: 'audio/webm',
              audioBitsPerSecond: 128000
            })
            
            // 音声データをWebM形式に変換
            const chunks: Blob[] = []
            mediaRecorder.ondataavailable = (e) => chunks.push(e.data)
            mediaRecorder.onstop = () => {
              const webmBlob = new Blob(chunks, { type: 'audio/webm' })
              const webmFile = new File([webmBlob], file.name.replace(/\.[^/.]+$/, '.webm'), {
                type: 'audio/webm'
              })
              resolve(webmFile)
            }
            
            // 変換開始
            mediaRecorder.start()
            source.start()
            
            // 変換完了
            setTimeout(() => {
              mediaRecorder.stop()
              source.stop()
              audioContext.close()
            }, audioBuffer.duration * 1000)
          } catch (error) {
            reject(error)
          }
        }
        reader.onerror = (error) => reject(error)
        reader.readAsArrayBuffer(file)
      } catch (error) {
        reject(error)
      }
    })
  }

  const handleVoiceMemoImport = async () => {
    console.log("Opening voice memo picker")
    // Implement voice memo import logic here
    // This might involve using a native API or a third-party library
  }

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles[0]) handleFileUpload(acceptedFiles[0])
    },
    [handleFileUpload, createdMeetingId, user],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "audio/*": [".mp3", ".m4a", ".wav"],
    },
    multiple: false,
  })

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-zinc-50 p-4">
        <div className="mx-auto max-w-[600px]">
          <div className="mb-8">
            <h1 className="text-xl font-medium">ページ1: 基本情報入力</h1>
          </div>

          <Card className="p-6">
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-medium">新規商談記録</h2>
                <p className="text-sm text-zinc-500">基本情報を入力してください</p>
              </div>

              <div className="space-y-4">
                {/* Meeting Date/Time */}
                <div className="space-y-1.5">
                  <Label className="flex items-center text-sm">実施日時</Label>
                  <div className="grid grid-cols-4 gap-2">
                    <Select value={formData.year} onValueChange={(value) => setFormData({ ...formData, year: value })}>
                      <SelectTrigger className="whitespace-nowrap text-sm h-9 [&>svg]:h-4 [&>svg]:w-4">
                        <SelectValue placeholder="年">
                          {formData.year && `${formData.year.slice(2)}年`}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {getYearOptions().map((year) => (
                          <SelectItem key={year} value={year.toString()} className="text-sm">
                            {year.toString().slice(2)}年
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Select value={formData.month} onValueChange={(value) => setFormData({ ...formData, month: value })}>
                      <SelectTrigger className="whitespace-nowrap text-sm h-9 [&>svg]:h-4 [&>svg]:w-4">
                        <SelectValue placeholder="月" />
                      </SelectTrigger>
                      <SelectContent>
                        {getMonthOptions().map((month) => (
                          <SelectItem key={month} value={month.toString().padStart(2, "0")}>
                            {month}月
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Select value={formData.day} onValueChange={(value) => setFormData({ ...formData, day: value })}>
                      <SelectTrigger className="whitespace-nowrap text-sm h-9 [&>svg]:h-4 [&>svg]:w-4">
                        <SelectValue placeholder="日" />
                      </SelectTrigger>
                      <SelectContent>
                        {getDayOptions().map((day) => (
                          <SelectItem key={day} value={day.toString().padStart(2, "0")}>
                            {day}日
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Select value={formData.hour} onValueChange={(value) => setFormData({ ...formData, hour: value })}>
                      <SelectTrigger className="whitespace-nowrap text-sm h-9 [&>svg]:h-4 [&>svg]:w-4">
                        <SelectValue placeholder="時" />
                      </SelectTrigger>
                      <SelectContent>
                        {getHourOptions().map((hour) => (
                          <SelectItem key={hour} value={hour.toString().padStart(2, "0")}>
                            {hour}:00
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Company Name (Business) */}
                <div className="space-y-1.5">
                  <Label htmlFor="companyNameBiz" className="flex items-center text-sm">
                    企業名
                    <span className="ml-1 text-sm text-red-500">*</span>
                  </Label>
                  <Input
                    id="companyNameBiz"
                    value={formData.companyNameBiz}
                    onChange={(e) => setFormData({ ...formData, companyNameBiz: e.target.value })}
                    placeholder="例：株式会社サンプル"
                  />
                </div>

                {/* Contact Person Name - 顧客名（担当者名） */}
                <div className="space-y-1.5">
                  <Label htmlFor="companyName" className="flex items-center text-sm">
                    顧客名（担当者名）
                    <span className="ml-1 text-sm text-red-500">*</span>
                  </Label>
                  <Input
                    id="companyName"
                    value={formData.companyName}
                    onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
                    placeholder="例：山田 太郎"
                  />
                </div>

                {/* Industry */}
                <div className="space-y-1.5">
                  <Label htmlFor="industry" className="flex items-center text-sm">
                    業種
                  </Label>
                  <Select
                    value={formData.industry}
                    onValueChange={(value) => setFormData({ ...formData, industry: value })}
                  >
                    <SelectTrigger id="industry" className="whitespace-nowrap text-sm h-9 [&>svg]:h-4 [&>svg]:w-4">
                      <SelectValue placeholder="選択してください" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="manufacturing" className="text-sm">製造業</SelectItem>
                      <SelectItem value="service">サービス業</SelectItem>
                      <SelectItem value="retail">小売業</SelectItem>
                      <SelectItem value="wholesale">卸売業</SelectItem>
                      <SelectItem value="construction">建設業</SelectItem>
                      <SelectItem value="it">IT・通信</SelectItem>
                      <SelectItem value="finance">金融・保険</SelectItem>
                      <SelectItem value="other">その他</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Scale */}
                <div className="space-y-1.5">
                  <Label htmlFor="scale" className="flex items-center text-sm">
                    規模
                  </Label>
                  <Select value={formData.scale} onValueChange={(value) => setFormData({ ...formData, scale: value })}>
                    <SelectTrigger id="scale" className="whitespace-nowrap text-sm h-9 [&>svg]:h-4 [&>svg]:w-4">
                      <SelectValue placeholder="選択してください" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="small">小規模 (従業員50人未満)</SelectItem>
                      <SelectItem value="medium">中規模 (従業員50-300人)</SelectItem>
                      <SelectItem value="large">大規模 (従業員300人以上)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Meeting Goal */}
                <div className="space-y-1.5">
                  <Label htmlFor="meetingGoal" className="flex items-center text-sm">
                    面談ゴール
                  </Label>
                  <Select
                    value={formData.meetingGoal}
                    onValueChange={(value) => setFormData({ ...formData, meetingGoal: value })}
                  >
                    <SelectTrigger id="meetingGoal" className="whitespace-nowrap text-sm h-9 [&>svg]:h-4 [&>svg]:w-4">
                      <SelectValue placeholder="選択してください" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="first">初回商談</SelectItem>
                      <SelectItem value="followup">フォローアップ</SelectItem>
                      <SelectItem value="closing">クロージング</SelectItem>
                      <SelectItem value="other">その他</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {submitError && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-600 text-sm">
                  {submitError}
                </div>
              )}

              {uploadStatus && (
                <div className={`mt-4 p-3 border rounded-md text-sm ${
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

              <div className="flex flex-col sm:flex-row gap-4 pt-4">
                <Button 
                  variant="outline" 
                  className="flex-1" 
                  onClick={() => handleSubmit("save")}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "保存中..." : "一時保存"}
                </Button>
                <div className="flex flex-1 gap-2">
                  {isMobile ? (
                    // Mobile version
                    <div className="flex gap-2 w-full">
                      <Button
                        variant="outline"
                        className="flex-1 whitespace-nowrap"
                        onClick={() => document.getElementById("file-upload")?.click()}
                        disabled={isUploading}
                      >
                        <Upload className="w-4 h-4 mr-2" />
                        {isUploading ? "アップロード中..." : "音声をアップロード"}
                      </Button>
                      <input
                        id="file-upload"
                        type="file"
                        accept="audio/*"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0]
                          if (file) handleFileUpload(file)
                        }}
                      />
                      <Button variant="outline" className="flex-none" onClick={handleVoiceMemoImport}>
                        <Mic className="w-4 h-4" />
                      </Button>
                    </div>
                  ) : (
                    // Desktop version
                    <div
                      {...getRootProps()}
                      className={`flex-1 relative ${
                        isDragActive ? "border-2 border-dashed border-primary" : ""
                      }`}
                    >
                      <input {...getInputProps()} />
                      <Button 
                        variant="outline" 
                        className="w-full whitespace-nowrap"
                        disabled={isUploading}
                      >
                        <Upload className="w-4 h-4 mr-2" />
                        {isUploading ? "アップロード中..." : "音声をアップロード"}
                      </Button>
                    </div>
                  )}
                  <Button 
                    className="flex-1 whitespace-nowrap" 
                    onClick={() => handleSubmit("next")}
                    disabled={isSubmitting || isUploading}
                  >
                    録音へ
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}

