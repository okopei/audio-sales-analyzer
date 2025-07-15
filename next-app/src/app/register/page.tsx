"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"

export default function RegisterPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    user_name: "",
    email: "",
    password: ""
  })
  const [isManager, setIsManager] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  // API のベース URL（ローカル開発用の URL）
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:7071'

  // バリデーション関数
  const validateForm = () => {
    if (!formData.user_name.trim()) {
      setError("名前は必須です")
      return false
    }
    if (!formData.email.trim()) {
      setError("メールアドレスは必須です")
      return false
    }
    if (!formData.password.trim()) {
      setError("パスワードは必須です")
      return false
    }
    if (formData.password.length < 6) {
      setError("パスワードは6文字以上で入力してください")
      return false
    }
    // メールアドレス形式チェック
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(formData.email)) {
      setError("正しいメールアドレス形式で入力してください")
      return false
    }
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    
    if (!validateForm()) {
      return
    }

    setLoading(true)
    
    try {
      console.log('🔍 新規登録処理開始:', { email: formData.email, user_name: formData.user_name, is_manager: isManager })
      
      const payload = {
        ...formData,
        is_manager: isManager
      }
      
      const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      
      console.log('🔍 新規登録 API レスポンス status:', response.status)
      
      const data = await response.json()
      console.log('🔍 新規登録 API レスポンス data:', data)
      
      if (!response.ok) {
        throw new Error(data.message || '登録に失敗しました')
      }
      
      if (data.success) {
        console.log('✅ 新規登録成功:', data)
        // 登録成功後、ログインページに遷移（成功メッセージ付き）
        router.push('/?registered=true')
      } else {
        throw new Error(data.message || '登録に失敗しました')
      }
    } catch (error) {
      console.error('❌ 新規登録処理でエラー:', error)
      setError(error instanceof Error ? error.message : "登録処理中にエラーが発生しました")
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
    // エラーメッセージをクリア
    if (error) {
      setError("")
    }
  }

  return (
    <div className="min-h-screen bg-[#1F1F1F] flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-6 bg-zinc-800 border-zinc-700">
        <h1 className="text-2xl font-bold text-center text-white mb-6">新規登録</h1>
        
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500 rounded text-red-500 text-sm mb-4">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            type="text"
            placeholder="名前"
            className="bg-zinc-800 border-zinc-700 text-white placeholder-zinc-400"
            value={formData.user_name}
            onChange={(e) => handleInputChange("user_name", e.target.value)}
            required
          />
          <Input
            type="email"
            placeholder="メールアドレス"
            className="bg-zinc-800 border-zinc-700 text-white placeholder-zinc-400"
            value={formData.email}
            onChange={(e) => handleInputChange("email", e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="パスワード（6文字以上）"
            className="bg-zinc-800 border-zinc-700 text-white placeholder-zinc-400"
            value={formData.password}
            onChange={(e) => handleInputChange("password", e.target.value)}
            required
          />
          <div className="flex items-center justify-between">
            <label className="text-sm text-zinc-300">
              マネージャーとして登録
            </label>
            <Switch
              checked={isManager}
              onCheckedChange={setIsManager}
            />
          </div>
          <Button 
            type="submit" 
            className="w-full bg-rose-500 text-white hover:bg-rose-600"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
                登録中...
              </>
            ) : (
              "登録"
            )}
          </Button>
        </form>
        
        <p className="text-sm text-center text-zinc-400 mt-4">
          既にアカウントをお持ちですか？
          <a href="/" className="text-rose-400 hover:underline">
            ログイン
          </a>
        </p>
      </Card>
    </div>
  )
}

