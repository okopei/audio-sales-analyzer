"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { EyeIcon, EyeOffIcon } from "lucide-react"
import { useRouter } from "next/navigation"
import { toast } from 'sonner'

interface RegisterForm {
  user_name: string
  email: string
  password: string
  role: 'manager' | 'member'
  manager_name?: string
}

interface ValidationErrors {
  user_name?: string
  email?: string
  password?: string
}

export default function RegisterPage() {
  const router = useRouter()
  const [formData, setFormData] = useState<RegisterForm>({
    user_name: "",
    email: "",
    password: "",
    role: "member",
    manager_name: ""
  })

  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<ValidationErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const validateForm = (): boolean => {
    const newErrors: ValidationErrors = {}

    // ユーザー名のバリデーション
    if (formData.user_name.length < 2) {
      newErrors.user_name = "ユーザー名は2文字以上で入力してください"
    }

    // メールアドレスのバリデーション
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(formData.email)) {
      newErrors.email = "有効なメールアドレスを入力してください"
    }

    // パスワードのバリデーション
    if (formData.password.length < 8) {
      newErrors.password = "パスワードは8文字以上で入力してください"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setErrors({})

    try {
      // TODO: 本番環境デプロイ時に環境変数に変更
      // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/register`, {
      const response = await fetch('http://localhost:7071/api/register/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = 'Registration failed'
        try {
          const errorData = JSON.parse(errorText)
          errorMessage = errorData.error || errorMessage
        } catch (e) {
          console.error('Error parsing error response:', errorText)
        }
        throw new Error(errorMessage)
      }

      const data = await response.json()
      console.log('Response:', data)

      toast.success('登録完了', {
        description: 'ユーザー登録が完了しました！',
        action: {
          label: 'ログインページへ',
          onClick: () => router.push('/')
        },
        duration: 4000
      })
      
      setTimeout(() => {
        router.push('/')
      }, 4000)

    } catch (error) {
      console.error('Error:', error)
      toast.error('登録に失敗しました', {
        description: error instanceof Error ? error.message : '予期せぬエラーが発生しました',
      })
      setErrors({ 
        password: error instanceof Error ? error.message : '登録に失敗しました' 
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-6">
        <h1 className="text-2xl font-semibold mb-6 text-center">ユーザー登録</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="user_name">ユーザー名</Label>
            <Input
              id="user_name"
              value={formData.user_name}
              onChange={(e) => setFormData({ ...formData, user_name: e.target.value })}
              required
              disabled={isSubmitting}
            />
            {errors.user_name && (
              <p className="text-sm text-red-500">{errors.user_name}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">メールアドレス</Label>
            <Input
              id="email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              disabled={isSubmitting}
            />
            {errors.email && (
              <p className="text-sm text-red-500">{errors.email}</p>
            )}
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
                disabled={isSubmitting}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOffIcon size={20} /> : <EyeIcon size={20} />}
              </button>
            </div>
            {errors.password && (
              <p className="text-sm text-red-500">{errors.password}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="role">役割</Label>
            <select
              id="role"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              value={formData.role}
              onChange={(e) => setFormData({ 
                ...formData, 
                role: e.target.value as 'manager' | 'member',
                ...(e.target.value === 'manager' ? {
                  manager_name: undefined
                } : {})
              })}
              disabled={isSubmitting}
            >
              <option value="member">メンバー</option>
              <option value="manager">マネージャー</option>
            </select>
          </div>
          
          {formData.role === 'member' && (
            <div className="space-y-2">
              <Label htmlFor="manager_name">マネージャー名</Label>
              <Input
                id="manager_name"
                type="text"
                value={formData.manager_name || ''}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  manager_name: e.target.value 
                })}
                required
                disabled={isSubmitting}
              />
            </div>
          )}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "登録中..." : "登録"}
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

