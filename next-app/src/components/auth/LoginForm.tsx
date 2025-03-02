"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/hooks/useAuth"
import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"

export default function LoginForm() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
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
    setIsLoading(true)

    try {
      await login(email, password)
      // リダイレクトは useAuth 内で処理されるため、ここでは何もしない
    } catch (err) {
      setError(err instanceof Error ? err.message : "ログインに失敗しました")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
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
          disabled={isLoading}
        >
          {isLoading ? (
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
      
      {/* 開発用のリンクは、本番環境では削除または条件付きで表示 */}
      <div className="pt-4 border-t border-zinc-800">
        <Button 
          variant="outline" 
          className="w-full border-zinc-700 text-zinc-400 hover:text-white"
          asChild
        >
          <a href="/dashboard">開発用ダッシュボード</a>
        </Button>
        <Button 
          variant="outline" 
          className="w-full border-zinc-700 text-zinc-400 hover:text-white"
          asChild
        >
          <a href="/manager-dashboard">開発用マネージャーダッシュボード</a>
        </Button>
      </div>
    </>
  )
} 