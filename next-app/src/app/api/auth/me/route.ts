import { NextRequest, NextResponse } from 'next/server'
import jwt from 'jsonwebtoken'

export async function GET(req: NextRequest) {
  try {
    const token = req.cookies.get('authToken')?.value
    
    if (!token) {
      console.log("❌ No authToken found in cookies")
      return NextResponse.json({ error: 'No token provided' }, { status: 401 })
    }
    
    // JWT_SECRETが設定されているかチェック
    const jwtSecret = process.env.JWT_SECRET
    if (!jwtSecret) {
      console.error('❌ JWT_SECRET is not configured')
      return NextResponse.json({ error: 'Server configuration error' }, { status: 500 })
    }
    
    // トークンの署名検証と期限チェック
    try {
      const decoded = jwt.verify(token, jwtSecret) as any
      
      // ユーザーIDを使ってAzure Functionからユーザー情報を取得
      const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL}/users/id/${decoded.user_id}`
      
      const response = await fetch(apiUrl)
      
      if (!response.ok) {
        console.log("❌ Failed to fetch user from Azure Function:", response.status)
        return NextResponse.json({ error: 'Failed to fetch user data' }, { status: 401 })
      }
      
      const userData = await response.json()
      
      // レスポンス形式を統一（userプロパティを含むオブジェクト）
      return NextResponse.json({ user: userData })
      
    } catch (jwtError) {
      console.error("❌ JWT検証エラー:", jwtError)
      return NextResponse.json({ error: 'Invalid token' }, { status: 401 })
    }
    
  } catch (error) {
    console.error("❌ /api/auth/me error:", error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
} 