"use client"

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/**
 * フィードバック一覧ページ
 * 要件：フィードバック画面は、ダッシュボード画面の過去商談一覧からのみ遷移可能
 * そのため、このページには直接アクセスできないよう、ダッシュボードにリダイレクトする
 */
export default function FeedbackListPage() {
  const router = useRouter()

  useEffect(() => {
    // フィードバック一覧へは直接アクセスせず、ダッシュボードへリダイレクト
    router.replace('/dashboard')
  }, [router])

  // リダイレクト中の表示
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
    </div>
  )
}

