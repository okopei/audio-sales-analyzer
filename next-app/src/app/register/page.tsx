"use client"

import Image from "next/image"
import { useRouter } from "next/navigation"

export default function RegisterPage() {
  const router = useRouter()
  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
      <div className="flex flex-col items-center justify-center py-10">
        <img
          src="/under_construction.png"
          alt="工事中"
          className="w-64 h-auto opacity-90"
        />
        <p className="mt-4 text-center text-gray-600 text-sm">
          新規登録機能は現在準備中です。
        </p>
        <button
          className="mt-8 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          onClick={() => router.push("/")}
        >
          ログイン画面に戻る
        </button>
      </div>
      {/*
      <Card className="w-full max-w-md p-6">
        <h1 className="text-2xl font-semibold mb-6 text-center">ユーザー登録</h1>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          ...（元のフォーム内容）...
        </form>
        <p className="mt-4 text-center text-sm text-zinc-600">
          既にアカウントをお持ちですか？
          <a href="/" className="text-blue-600 hover:underline">
            ログイン
          </a>
        </p>
      </Card>
      */}
    </div>
  )
}

