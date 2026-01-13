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
        authorized: async ({ auth }) => {
            // Logged in users are authenticated, otherwise redirect to login
            return !!auth
        },
    },
})
