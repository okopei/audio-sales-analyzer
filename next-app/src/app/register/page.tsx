"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { EyeIcon, EyeOffIcon } from "lucide-react"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { useRouter } from "next/navigation"

export default function RegisterPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    role: "member", // デフォルトは一般ユーザー
    account_status: "ACTIVE",
  })

  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError("")

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/register/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          user_name: formData.username,
        }),
      })

      const data = await response.json()

      if (response.ok && data.success) {
        console.log("Registration successful:", data)
        router.push("/?registered=true")
      } else {
        setError(data.message || "登録に失敗しました")
      }
    } catch (err) {
      console.error("Registration error:", err)
      setError("登録中にエラーが発生しました")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-6">
        <h1 className="text-2xl font-semibold mb-6 text-center">ユーザー登録</h1>
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">ユーザー名</Label>
            <Input
              id="username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="email">メールアドレス</Label>
            <Input
              id="email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="password">パスワード設定</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOffIcon size={20} /> : <EyeIcon size={20} />}
              </button>
            </div>
          </div>
          
          <div className="space-y-2">
            <Label>ユーザータイプ</Label>
            <RadioGroup
              value={formData.role}
              onValueChange={(value) => setFormData({ ...formData, role: value })}
              className="flex space-x-4"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="member" id="member" />
                <Label htmlFor="member">一般ユーザー</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="manager" id="manager" />
                <Label htmlFor="manager">マネージャー</Label>
              </div>
            </RadioGroup>
          </div>
          
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "登録中..." : "登録"}
          </Button>
        </form>
        
        <p className="mt-4 text-center text-sm text-zinc-600">
          既にアカウントをお持ちですか？
          <a href="/" className="text-blue-600 hover:underline">
            ログイン
          </a>
        </p>
      </Card>
    </div>
  )
}

