import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

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

  // ユーザーデータがある場合はパース
  let user = null
  let isManager = false
  
  if (userStr) {
    try {
      user = JSON.parse(userStr)
      isManager = user?.is_manager === true || user?.role === 'manager'
    } catch (error) {
      console.error('Error parsing user data:', error)
    }
  }

  // 認証状態
  const isAuthenticated = !!token && !!user

  // 保護されたルートへのアクセスで未認証の場合
  if (protectedRoutes.some(route => pathname.startsWith(route)) && !isAuthenticated) {
    console.log(`Unauthenticated access to ${pathname}, redirecting to login`)
    return NextResponse.redirect(new URL('/', request.url))
  }

  // マネージャー限定ページにマネージャー以外がアクセスした場合
  if (managerOnlyRoutes.some(route => pathname.startsWith(route)) && isAuthenticated && !isManager) {
    console.log(`Non-manager access to ${pathname}, redirecting to dashboard`)
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  // 認証済みのユーザーがログインページや登録ページへアクセスした場合
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
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|.*\\.png$).*)'],
} 