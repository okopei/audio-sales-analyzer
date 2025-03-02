import { Suspense } from 'react'
import dynamic from 'next/dynamic'

// クライアントコンポーネントを動的にインポート
const LoginForm = dynamic(() => import('@/components/auth/LoginForm'), {
  ssr: false, // サーバーサイドレンダリングを無効化
})

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-[#1F1F1F] flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <h1 className="text-2xl font-bold text-center text-white">ログイン</h1>
        <Suspense fallback={<div className="text-white text-center">読み込み中...</div>}>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  )
}