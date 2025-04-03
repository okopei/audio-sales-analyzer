"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Cookies from 'js-cookie'

/**
 * テスト用ナビゲーションコンポーネント
 * 固定のuser_id=27を使用した認証をシミュレートする
 * 
 * 【注意】このコンポーネントは開発/テスト用であり、リリース前に削除すること
 */
export default function TestNavigation() {
  const router = useRouter()
  const [statusMessage, setStatusMessage] = useState('')

  // テスト用の認証データ（要削除）- useAuthと同じ形式に合わせる
  const testUser = {
    user_id: 27, // テスト用固定ユーザーID（要削除）
    email: "test@example.com",
    user_name: "テストユーザー",
    is_manager: true,
    role: "manager"
  }

  // 本番と同様の形式のトークン（テスト用）
  const testToken = "test-token-for-development-" + Date.now()

  // アプリ内の全ての画面へのナビゲーションリンク
  const navLinks = [
    { name: 'ダッシュボード', path: '/dashboard', needsAuth: true },
    { name: 'マネージャーダッシュボード', path: '/manager-dashboard', needsAuth: true },
    { name: '新規商談', path: '/newmeeting', needsAuth: true },
    { name: '録音', path: '/recording', needsAuth: true },
    { name: '商談検索', path: '/search', needsAuth: true },
    { name: '新規登録', path: '/register', needsAuth: false },
    { name: 'アップロードテスト', path: '/test-upload', needsAuth: true },
  ]

  // テスト用の認証情報をセットアップして指定ページに遷移する関数（要削除）
  const navigateWithAuth = (path: string) => {
    try {
      // 認証データをuseAuthフックと同じ形式で設定
      const userData = JSON.stringify(testUser)
      
      // Cookie有効期限（7日間 - useAuthと同じ）
      const COOKIE_EXPIRY = 7
      
      // ローカルストレージに認証情報を保存
      localStorage.setItem('user', userData)
      localStorage.setItem('token', testToken)
      
      // Cookieにも保存（ミドルウェア用）- js-cookieを使用してuseAuthと同じ方法
      Cookies.set('user', userData, { expires: COOKIE_EXPIRY })
      Cookies.set('authToken', testToken, { expires: COOKIE_EXPIRY })
      
      // ステータスメッセージ更新
      setStatusMessage(`認証情報をセット (ID:${testUser.user_id})...`)
      
      // 遷移処理
      setTimeout(() => {
        // window.location.hrefを使用して完全なページリロードで遷移（ミドルウェア確実に動作させる）
        window.location.href = path
      }, 500)
    } catch (error) {
      setStatusMessage('エラーが発生しました')
      console.error('テストナビゲーションエラー:', error)
    }
  }

  return (
    <div className="absolute top-4 left-4 z-50">
      <Card className="p-3 bg-yellow-500/20 border border-yellow-500">
        <div className="text-xs font-bold text-yellow-400 mb-2">
          テスト用ナビゲーション（要削除）<br/>
          <span className="text-[10px] text-yellow-300">※固定user_id=27使用</span>
        </div>
        <div className="text-[10px] bg-yellow-800/30 text-yellow-300 p-1 rounded mb-2">
          注意: ログイン画面に戻りたい場合は、ダッシュボード画面からログアウトを行う
        </div>
        {statusMessage && (
          <div className="text-[10px] bg-green-800/30 text-green-400 p-1 rounded mb-2">
            {statusMessage}
          </div>
        )}
        <div className="flex flex-col gap-1">
          {navLinks.map((link) => 
            link.needsAuth ? (
              <Button 
                key={link.path}
                variant="link" 
                size="sm"
                className="text-xs text-white hover:text-yellow-400 transition-colors p-0 h-auto justify-start font-normal"
                onClick={() => navigateWithAuth(link.path)}
              >
                → {link.name}
              </Button>
            ) : (
              <Link 
                key={link.path} 
                href={link.path}
                className="text-xs text-white hover:text-yellow-400 transition-colors"
              >
                → {link.name}
              </Link>
            )
          )}
        </div>
      </Card>
    </div>
  )
} 