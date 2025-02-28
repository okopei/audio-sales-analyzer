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
import { saveMeeting } from "@/lib/api-client"

// 仮のユーザーデータ（実際の実装では認証システムから取得）
const currentUser = {
  id: "user123",
  name: "山田 太郎",
}

export default function NewMeetingPage() {
  const router = useRouter()
  const { startRecording } = useRecording()
  const [isMobile, setIsMobile] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

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
    contactPerson: currentUser.name,
    industry: "",
    scale: "",
    meetingGoal: "",
  })

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

  const handleSubmit = async (type: "save" | "next") => {
    if (!formData.companyName) {
      alert("顧客名は必須です")
      return
    }
    
    setIsSubmitting(true)
    setSubmitError(null)
    
    try {
      console.log("Submitting form data:", formData);
      
      // API を呼び出して商談情報を保存
      const response = await saveMeeting(formData)
      
      console.log("Meeting saved successfully:", response)
      
      // 成功時の処理
      if (type === "next") {
        // 録音ページへ移動（会議IDを渡す）
        await startRecording()
        router.push(`/recording?recording=true&meetingId=${response.meetingId}`)
      } else {
        // 保存成功メッセージを表示
        alert(`保存完了: ${response.message}`)
      }
    } catch (error) {
      console.error("Error saving meeting:", error)
      // エラーメッセージを表示
      setSubmitError(error instanceof Error ? error.message : "商談情報の保存に失敗しました")
      alert("エラー: 商談情報の保存に失敗しました")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleStartRecording = async () => {
    await startRecording()
    router.push("/recording?recording=true")
  }

  const handleFileUpload = async (file: File) => {
    console.log("Uploading file:", file)
    // Implement your file upload logic here
    // For example, you might use the Vercel Blob API to upload the file
    // const { url } = await upload(file.name, file, { access: 'public' })
    // console.log('File uploaded to:', url)
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
    [handleFileUpload],
  ) // Added handleFileUpload to dependencies

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "audio/*": [".mp3", ".m4a", ".wav"],
    },
    multiple: false,
  })

  return (
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

              {/* Company Name */}
              <div className="space-y-1.5">
                <Label htmlFor="companyName" className="flex items-center text-sm">
                  顧客
                  <span className="ml-1 text-sm text-red-500">*</span>
                </Label>
                <Input
                  id="companyName"
                  value={formData.companyName}
                  onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
                  placeholder="例：株式会社サンプル"
                />
              </div>

              {/* Contact Person - Auto-filled */}
              <div className="space-y-1.5">
                <Label htmlFor="contactPerson" className="flex items-center text-sm">
                  担当者名
                </Label>
                <Input id="contactPerson" value={formData.contactPerson} disabled className="bg-zinc-50" />
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
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      音声をアップロード
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
                    className={`flex-1 relative ${isDragActive ? "border-2 border-dashed border-primary" : ""}`}
                  >
                    <input {...getInputProps()} />
                    <Button variant="outline" className="w-full whitespace-nowrap">
                      <Upload className="w-4 h-4 mr-2" />
                      音声をアップロード
                    </Button>
                  </div>
                )}
                <Button 
                  className="flex-1 whitespace-nowrap" 
                  onClick={() => handleSubmit("next")}
                  disabled={isSubmitting}
                >
                  録音へ
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

