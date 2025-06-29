"use client"

import { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useSearchParams } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

// テスト用ナビゲーションコンポーネント（要削除）
const TestNavigation = dynamic(() => import('@/components/TestNavigation'), {
  ssr: false
})

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const { login, loading } = useAuth()
  const searchParams = useSearchParams()

  // 登録成功時のメッセージを表示
  useEffect(() => {
    const registered = searchParams.get("registered")
    if (registered === "true") {
      setSuccessMessage("ユーザー登録が完了しました。ログインしてください。")
    }
  }, [searchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    try {
      await login(email, password)
      // リダイレクトは useAuth 内で処理されるため、ここでは何もしない
    } catch (err) {
      setError(err instanceof Error ? err.message : "ログインに失敗しました")
    }
  }

  return (
    <div className="min-h-screen bg-[#1F1F1F] flex items-center justify-center p-4 relative">
      {/* テスト用ナビゲーション（要削除） */}
      <TestNavigation />

      <div className="w-full max-w-sm space-y-6">
        <h1 className="text-2xl font-bold text-center text-white">ログイン</h1>
        
        {successMessage && (
          <div className="p-3 bg-green-500/10 border border-green-500 rounded text-green-500 text-sm">
            {successMessage}
          </div>
        )}
        
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500 rounded text-red-500 text-sm">
            {error}
          </div>
        )}
        
        <form className="space-y-4" onSubmit={handleSubmit}>
          <Input
            type="email"
            placeholder="メールアドレス"
            className="bg-zinc-800 border-zinc-700 text-white placeholder-zinc-400"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="パスワード"
            className="bg-zinc-800 border-zinc-700 text-white placeholder-zinc-400"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button 
            type="submit" 
            className="w-full bg-rose-500 text-white hover:bg-rose-600"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
                ログイン中...
              </>
            ) : (
              "ログイン"
            )}
          </Button>
        </form>
        
        <p className="text-sm text-center text-zinc-400">
          アカウントをお持ちでない方は
          <a href="/register" className="text-rose-400 hover:underline">
            新規登録
          </a>
        </p>
      </div>
    </div>
  )
}