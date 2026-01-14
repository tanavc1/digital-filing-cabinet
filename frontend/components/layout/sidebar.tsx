"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search, Files, Building, ShieldCheck, Shield, GitCompare } from "lucide-react";
import { cn } from "@/lib/utils";
import { useWorkspace } from "../providers/workspace-provider";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

export function Sidebar() {
    const pathname = usePathname();
    const { workspace, setSelectedWorkspace, availableWorkspaces, docs, workspaceCounts } = useWorkspace(); // Get docs & counts

    const handleWorkspaceChange = (val: string) => {
        const found = availableWorkspaces.find((w) => w.id === val);
        if (found) setSelectedWorkspace(found.id);
    };

    const navItems = [
        { href: "/", label: "Search", icon: Search },
        { href: "/documents", label: "Documents", icon: Files, count: docs?.length },
        { href: "/audit", label: "Audit", icon: Shield },
        { href: "/compare", label: "Compare", icon: GitCompare },
    ];

    return (
        <div className="w-64 border-r h-screen bg-gray-50/50 flex flex-col">
            {/* Workspace Header */}
            <div className="p-4 border-b">
                <div className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Workspace
                </div>
                <Select value={workspace.id} onValueChange={handleWorkspaceChange}>
                    <SelectTrigger className="w-full bg-white">
                        <div className="flex items-center gap-2">
                            <Building className="w-4 h-4 text-gray-500" />
                            <SelectValue placeholder="Select workspace" />
                        </div>
                    </SelectTrigger>
                    <SelectContent>
                        {availableWorkspaces.map((w) => (
                            <SelectItem key={w.id} value={w.id}>
                                <span className="font-medium">{w.label}</span>
                                <span className="ml-2 text-xs text-gray-400">
                                    ({workspaceCounts[w.id] ?? 0})
                                </span>
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            {/* Nav */}
            <nav className="flex-1 p-4 space-y-1">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                                isActive
                                    ? "bg-gray-200 text-gray-900"
                                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                            )}
                        >
                            <item.icon className="w-4 h-4" />
                            <span className="flex-1">{item.label}</span>
                            {item.count !== undefined && (
                                <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
                                    {item.count}
                                </span>
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer / Status */}
            <div className="p-4 border-t bg-white">
                <div className="flex items-center gap-2 text-xs text-green-600 font-medium">
                    <ShieldCheck className="w-3 h-3" />
                    <span>Evidence Enforcement Active</span>
                </div>
                <div className="mt-1 text-[10px] text-gray-400">
                    Backend: {process.env.NEXT_PUBLIC_API_URL || "Connected"}
                </div>
            </div>
        </div>
    );
}
