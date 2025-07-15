import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import jwt from 'jsonwebtoken'

// 認証が必要なページのパス
const protectedRoutes = ['/dashboard', '/manager-dashboard', '/search', '/feedback', '/recording', '/newmeeting']
// 認証されていない場合にアクセスできるページのパス
const publicRoutes = ['/', '/register']
// マネージャーのみがアクセスできるページのパス
const managerOnlyRoutes = ['/manager-dashboard']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get('authToken')?.value
  const userStr = request.cookies.get('user')?.value

  // JWTトークンの検証
  let isAuthenticated = false
  let user = null
  let isManager = false

  if (token) {
    try {
      // JWT_SECRETが設定されているかチェック
      const jwtSecret = process.env.JWT_SECRET
      if (!jwtSecret) {
        console.error('❌ JWT_SECRET is not configured')
        return NextResponse.redirect(new URL('/', request.url))
      }

      // トークンの署名検証と期限チェック
      const decoded = jwt.verify(token, jwtSecret) as any
      
      isAuthenticated = true
    } catch (error) {
      console.error('❌ JWT verification failed:', error)
      // 無効なトークンの場合、Cookieを削除してログインページへリダイレクト
      const response = NextResponse.redirect(new URL('/', request.url))
      response.cookies.set('authToken', '', { maxAge: 0, path: '/' })
      response.cookies.set('user', '', { maxAge: 0, path: '/' })
      return response
    }
  }

  // ユーザーデータがある場合はパース
  if (userStr) {
    try {
      user = JSON.parse(userStr)
      isManager = user?.is_manager === true || user?.role === 'manager'
    } catch (error) {
      console.error('Error parsing user data:', error)
    }
  }

  // 保護されたルートへのアクセスで未認証の場合
  if (protectedRoutes.some(route => pathname.startsWith(route)) && !isAuthenticated) {
    console.log(`❌ Unauthenticated access to ${pathname}, redirecting to login`)
    console.log(`🔍 Protected routes check:`, {
      pathname,
      isProtected: protectedRoutes.some(route => pathname.startsWith(route)),
      isAuthenticated
    })
    return NextResponse.redirect(new URL('/', request.url))
  }

  // マネージャー限定ページにマネージャー以外がアクセスした場合
  if (managerOnlyRoutes.some(route => pathname.startsWith(route)) && isAuthenticated && !isManager) {
    console.log(`Non-manager access to ${pathname}, redirecting to dashboard`)
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  // 認証済みのユーザーがログインページへアクセスした場合
  if (publicRoutes.includes(pathname) && isAuthenticated) {
    if (pathname === '/') {
      console.log(`Authenticated user on login page, redirecting to appropriate dashboard`)
      if (isManager) {
        return NextResponse.redirect(new URL('/manager-dashboard', request.url))
      } else {
        return NextResponse.redirect(new URL('/dashboard', request.url))
      }
    }
  }

  return NextResponse.next()
}

// ミドルウェアを適用するパスを設定
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api/auth (auth API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - .png files
     */
    '/((?!api/auth|_next/static|_next/image|favicon.ico|.*\\.png$).*)',
  ],
} 