"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

// 仮のユーザーデータ（実際の実装では認証システムから取得）
const currentUser = {
  id: "user123",
  name: "山田 太郎",
}

export default function NewMeetingPage() {
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
    meetingGoal: "", // Updated: meetingCall -> meetingGoal
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

  const handleSubmit = (type: "save" | "next") => {
    if (!formData.companyName) {
      alert("顧客名は必須です")
      return
    }
    console.log("Submitting form:", { type, formData })
  }

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
              {/* Meeting Date/Time - Required */}
              <div className="space-y-1.5">
                <Label className="flex items-center text-sm">
                  実施日時
                  {/* Removed: <span className="ml-1 text-sm text-red-500">*</span> */}
                </Label>
                <div className="grid grid-cols-4 gap-2">
                  <Select value={formData.year} onValueChange={(value) => setFormData({ ...formData, year: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="年" />
                    </SelectTrigger>
                    <SelectContent>
                      {getYearOptions().map((year) => (
                        <SelectItem key={year} value={year.toString()}>
                          {year}年
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Select value={formData.month} onValueChange={(value) => setFormData({ ...formData, month: value })}>
                    <SelectTrigger>
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
                    <SelectTrigger>
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
                    <SelectTrigger>
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
                  {/* Removed: <span className="ml-1 text-sm text-red-500">*</span> */}
                </Label>
                <Input id="contactPerson" value={formData.contactPerson} disabled className="bg-zinc-50" />
              </div>

              {/* Industry */}
              <div className="space-y-1.5">
                <Label htmlFor="industry" className="flex items-center text-sm">
                  業種
                  {/* Removed: <span className="ml-1 text-sm text-red-500">*</span> */}
                </Label>
                <Select
                  value={formData.industry}
                  onValueChange={(value) => setFormData({ ...formData, industry: value })}
                >
                  <SelectTrigger id="industry">
                    <SelectValue placeholder="選択してください" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manufacturing">製造業</SelectItem>
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
                  {/* Removed: <span className="ml-1 text-sm text-red-500">*</span> */}
                </Label>
                <Select value={formData.scale} onValueChange={(value) => setFormData({ ...formData, scale: value })}>
                  <SelectTrigger id="scale">
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
                  {/* Removed: <span className="ml-1 text-sm text-red-500">*</span> */}
                </Label>
                <Select
                  value={formData.meetingGoal} // Updated: formData.meetingGoal
                  onValueChange={(value) => setFormData({ ...formData, meetingGoal: value })} // Updated: meetingGoal
                >
                  <SelectTrigger id="meetingGoal">
                    {" "}
                    {/* Updated: meetingGoal */}
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

            <div className="flex gap-4 pt-4">
              <Button variant="outline" className="flex-1" onClick={() => handleSubmit("save")}>
                一時保存
              </Button>
              <Button className="flex-1" onClick={() => handleSubmit("next")}>
                商談プラン作成へ
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
