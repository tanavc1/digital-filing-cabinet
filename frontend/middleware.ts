import { auth } from "@/auth"

export const config = {
    matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}

export default auth((req) => {
    const needsAuth = req.nextUrl.pathname === "/" || req.nextUrl.pathname.startsWith("/chat")
    const isLoggedIn = !!req.auth

    if (needsAuth && !isLoggedIn) {
        const newUrl = new URL("/login", req.nextUrl.origin)
        return Response.redirect(newUrl)
    }
})
