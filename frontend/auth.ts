import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"

export const { handlers, signIn, signOut, auth } = NextAuth({
    providers: [
        Credentials({
            credentials: {
                password: { label: "Password", type: "password" },
            },
            authorize: async (credentials) => {
                // Admin password must be set via ADMIN_PASSWORD env var
                const pw = process.env.ADMIN_PASSWORD
                if (!pw) {
                    console.error("ADMIN_PASSWORD env var not set — login disabled")
                    return null
                }

                if (credentials.password === pw) {
                    return { id: "1", name: "Admin User", email: "admin@local" }
                }

                // Return null if validation fails
                return null
            },
        }),
    ],
    pages: {
        signIn: "/login", // Custom login page
    },
    callbacks: {
        authorized: async ({ auth, request }) => {
            const isLoggedIn = !!auth?.user
            const isOnLoginPage = request.nextUrl.pathname.startsWith('/login')

            if (isOnLoginPage) {
                if (isLoggedIn) {
                    return Response.redirect(new URL('/', request.nextUrl))
                }
                return true // Allow access to login page
            }

            return isLoggedIn // Require auth for all other pages
        },
    },
    trustHost: true,
})
