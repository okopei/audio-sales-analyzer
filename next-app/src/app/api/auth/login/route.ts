import { NextRequest, NextResponse } from 'next/server'
import jwt from 'jsonwebtoken'

export async function POST(req: NextRequest) {
  const { email, password } = await req.json()

  try {
    const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL}/users/login`
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    const result = await response.json()

    if (!response.ok) {
      console.log("❌ Azure Function error:", result)
      return NextResponse.json({ error: result.error || 'Login failed' }, { status: 401 })
    }

    if (!result.user) {
      console.error("❌ Azure Function response に user が含まれていません")
      return NextResponse.json({ error: 'Invalid response from Azure Function' }, { status: 500 })
    }

    const user = result.user

    // JWTトークンの生成
    const jwtSecret = process.env.JWT_SECRET
    
    if (!jwtSecret) {
      console.error('❌ JWT_SECRET is not configured')
      return NextResponse.json({ error: 'Server configuration error' }, { status: 500 })
    }

    // JWTトークンを生成
    const token = jwt.sign(
      { 
        user_id: user.user_id, 
        is_manager: user.is_manager 
      }, 
      jwtSecret, 
      { expiresIn: '7d' }
    )

    const res = NextResponse.json({ success: true, user })
    
    // Cookie設定
    res.cookies.set('authToken', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7,
    })

    return res
  } catch (error) {
    console.error("❌ /api/auth/login error:", error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
} 