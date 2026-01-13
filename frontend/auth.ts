import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"

export const { handlers, signIn, signOut, auth } = NextAuth({
    providers: [
        Credentials({
            credentials: {
                password: { label: "Password", type: "password" },
            },
            authorize: async (credentials) => {
                // Simple admin password check
                // In production, use a hash match (bcrypt) or external DB
                const pw = process.env.ADMIN_PASSWORD || "admin"

                if (credentials.password === pw) {
                    // Return a user object
                    return { id: "1", name: "Admin User", email: "admin@example.com" }
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
