"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "./sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isLoginPage = pathname === "/login";

    if (isLoginPage) {
        return <main className="flex-1 min-h-screen bg-white">{children}</main>;
    }

    return (
        <div className="flex h-screen w-full bg-white text-gray-900 antialiased">
            <Sidebar />
            <main className="flex-1 overflow-auto bg-white">
                {children}
            </main>
        </div>
    );
}
