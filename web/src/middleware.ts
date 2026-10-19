import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const hasSession = request.cookies.has("mn_session")

  // Paths that don't need authentication
  const publicPaths = ["/login", "/register"]
  const isPublicPath = publicPaths.some((path) => pathname.startsWith(path))
  const isApiPath = pathname.startsWith("/api/")
  const isStaticPath = pathname.startsWith("/_next/") || pathname.startsWith("/static/") || pathname === "/favicon.ico"

  // If it's an API route or static file, allow
  if (isApiPath || isStaticPath) {
    return NextResponse.next()
  }

  // If public path (/login, /register)
  if (isPublicPath) {
    // If has session, redirect to dashboard
    if (hasSession) {
      return NextResponse.redirect(new URL("/dashboard", request.url))
    }
    // If no session, allow
    return NextResponse.next()
  }

  // If not public path
  // If no session, redirect to login
  if (!hasSession) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("callbackUrl", pathname + request.nextUrl.search)
    return NextResponse.redirect(loginUrl)
  }

  // Has session and not public path, allow
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
}
