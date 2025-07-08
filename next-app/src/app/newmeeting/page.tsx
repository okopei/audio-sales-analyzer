"use client"

import { useState, useEffect, useCallback, useRef } from "react"
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

// APIレスポンスの型定義
interface BasicInfoResponse {
  message: string
  meeting_id: number
  search_info?: {
    meeting_id: number
    user_id: number
    client_company_name: string
    client_contact_name: string
    meeting_datetime: string
  }
}

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
  const submitTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const lastSubmitTimeRef = useRef<number>(0)
  
  // デバウンス時間（ミリ秒）
  const DEBOUNCE_TIME = 2000

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
    // デバウンス処理
    const now = Date.now()
    if (now - lastSubmitTimeRef.current < DEBOUNCE_TIME) {
      console.log("送信をスキップ: 前回の送信から2秒以内です")
      return null
    }
    lastSubmitTimeRef.current = now

    if (isSubmitting) {
      console.log("送信をスキップ: 既に送信中です")
      return null
    }

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

      // 既存のsubmitTimeoutRefをクリア
      if (submitTimeoutRef.current) {
        clearTimeout(submitTimeoutRef.current)
        submitTimeoutRef.current = null
      }

      // 新しいタイムアウトを設定
      submitTimeoutRef.current = setTimeout(() => {
        setIsSubmitting(false)
        submitTimeoutRef.current = null
      }, DEBOUNCE_TIME)

      // 会議日時文字列を作成
      const meeting_datetime = `${formData.year}-${formData.month.padStart(2, "0")}-${formData.day.padStart(2, "0")} ${formData.hour.padStart(2, "0")}:00:00`;
      
      // Save basic info
      const basicInfoData = {
        user_id: user.user_id,
        year: formData.year,
        month: formData.month,
        day: formData.day,
        hour: formData.hour,
        client_contact_name: formData.companyName,
        client_company_name: formData.companyNameBiz,
        industry: formData.industry,
        scale: formData.scale,
        meeting_goal: formData.meetingGoal,
        meeting_datetime: meeting_datetime,
      }

      console.log("Submitting form data:", basicInfoData);
      
      // API を呼び出して商談情報を保存（BasicInfoテーブルに保存）
      const response = await saveBasicInfo(basicInfoData) as BasicInfoResponse
      
      console.log("BasicInfo saved successfully:", response)
      
      // 会議IDの取得を確認
      if (!response.meeting_id) {
        throw new Error("会議IDの取得に失敗しました")
      }
      
      // 基本情報をローカルストレージに保存
      try {
        const basicMeetingInfo = {
          user_id: user.user_id,
          client_company_name: formData.companyNameBiz,
          client_contact_name: formData.companyName,
          meeting_datetime: meeting_datetime
        }
        
        localStorage.setItem('basicMeetingInfo', JSON.stringify(basicMeetingInfo))
        
        // responseから検索情報を取得
        if (response.search_info) {
          console.log("検索情報をローカルストレージに保存:", response.search_info)
        }
        
        console.log("基本情報をローカルストレージに保存:", basicMeetingInfo)
      } catch (storageError) {
        console.warn("ローカルストレージへの保存に失敗:", storageError)
      }
      
      // 成功時の処理
      if (type === "next") {
        // 会議IDの取得
        console.log("BasicInfo保存完了、検索情報:", response.search_info)
        
        // 商談情報の保存完了をトーストで通知
        toast.success("商談情報を保存しました。録音画面に移動します")
        
        // データベースへの反映を確実にするために少し待機
        setTimeout(() => {
          console.log("録音画面へ移動します")
          // 録音ページへ移動
          router.push(`/recording`)
        }, 1000)
      } else {
        // 保存成功メッセージを表示
        toast.success(`商談情報を保存しました: ${response.message}`)
        // 会議IDを返す
        return response.meeting_id
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
      // タイムアウトをクリア
      if (submitTimeoutRef.current) {
        clearTimeout(submitTimeoutRef.current)
      }
      setIsSubmitting(false)
    }
    
    return null
  }

  // コンポーネントのアンマウント時にタイムアウトをクリア
  useEffect(() => {
    return () => {
      if (submitTimeoutRef.current) {
        clearTimeout(submitTimeoutRef.current)
      }
    }
  }, [])

  const handleFileUpload = async (file: File) => {
    console.log("🔍[UPLOAD] 受け取ったファイル:", file)
    console.log("🔍[UPLOAD] ファイル名:", file.name)
    console.log("🔍[UPLOAD] MIMEタイプ:", file.type)
    console.log("🔍[UPLOAD] ファイルサイズ:", (file.size / 1024 / 1024).toFixed(2), "MB")

    if (!user) {
      console.error("❌[UPLOAD] ユーザー未ログイン")
      toast.error("ログインしてください")
      return
    }
    
    try {
      setIsUploading(true)
      setUploadStatus({ message: "商談情報を保存しています..." })
      
      // 基本情報を保存して会議IDを取得
      console.log("📝[UPLOAD] 商談情報の保存を開始")
      const meetingId = await handleSubmit("save")
      
      if (!meetingId) {
        console.error("❌[UPLOAD] 会議IDの取得に失敗")
        setUploadStatus({
          success: false,
          message: "商談情報の保存に失敗しました。もう一度お試しください。"
        })
        return
      }
      
      console.log("✅[UPLOAD] 会議ID取得成功:", meetingId)
      
      setUploadStatus({ message: "音声をアップロード中..." })
      
      // meeting_idとuser_idを含むファイル名を生成
      const userId = user.user_id
      const now = new Date()
      const timestamp = now.toISOString().replace(/[:.]/g, '-').replace('Z', '')
      const fileName = `meeting_${meetingId}_user_${userId}_${timestamp}${file.name.substring(file.name.lastIndexOf('.'))}`
      
      console.log("📝[UPLOAD] アップロード用ファイル名:", fileName)
      
      // Azure Blob Storageにアップロード（変換せずそのまま）
      console.log("📤[UPLOAD] Azure Blob Storageへのアップロード開始")
      const blobUrl = await uploadToAzureStorage(file, fileName)
      
      console.log("✅[UPLOAD] アップロード成功:", blobUrl)
      
      setUploadStatus({
        success: true,
        message: "音声のアップロードに成功しました。ダッシュボードに移動します...",
        url: blobUrl
      })
      
      // 成功メッセージ表示後、ダッシュボードに遷移
      console.log("🔄[UPLOAD] ダッシュボードへの遷移準備")
      setTimeout(() => {
        if (user?.account_status === 'ACTIVE' && user?.is_manager) {
          console.log("🔄[UPLOAD] マネージャーダッシュボードへ遷移")
          router.push('/manager-dashboard')
        } else {
          console.log("��[UPLOAD] 一般ダッシュボードへ遷移")
          router.push('/dashboard')
        }
      }, 2000)
    } catch (error) {
      console.error("❌[UPLOAD] アップロードエラー:", error)
      let errorMessage = "アップロードに失敗しました"
      
      if (error instanceof Error) {
        if (error.message.includes("BlobStorage")) {
          console.error("❌[UPLOAD] BlobStorageエラー:", error.message)
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
                    {isSubmitting ? "処理中..." : "録音へ"}
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

