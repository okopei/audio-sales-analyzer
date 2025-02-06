import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-[#1F1F1F] flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <h1 className="text-2xl font-bold text-center text-white">ログイン</h1>
        <form className="space-y-4">
          <Input
            type="email"
            placeholder="メールアドレス"
            className="bg-zinc-800 border-zinc-700 text-white placeholder-zinc-400"
          />
          <Input
            type="password"
            placeholder="パスワード"
            className="bg-zinc-800 border-zinc-700 text-white placeholder-zinc-400"
          />
          <Button className="w-full bg-rose-500 text-white hover:bg-rose-600">ログイン</Button>
        </form>
        <p className="text-sm text-center text-zinc-400">
          アカウントをお持ちでない方は
          <a href="/signup" className="text-rose-400 hover:underline">
            新規登録
          </a>
        </p>
      </div>
    </div>
  )
}

