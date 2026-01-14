"use client";

import { FolderOpen, ChevronDown, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Doc } from "@/lib/types";

interface FolderFilterProps {
    docs: Doc[];
    selectedFolder: string | null;
    onSelect: (folder: string | null) => void;
}

export function FolderFilter({ docs, selectedFolder, onSelect }: FolderFilterProps) {
    // Extract unique folder paths from docs
    const folders = Array.from(
        new Set(
            docs
                .map((doc) => doc.folder_path)
                .filter((fp): fp is string => !!fp && fp.length > 0)
        )
    ).sort();

    // Don't render if no folders exist
    if (folders.length === 0) {
        return null;
    }

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant="outline"
                    size="sm"
                    className="gap-2 text-sm font-medium"
                >
                    <FolderOpen className="w-4 h-4 text-amber-500" />
                    {selectedFolder || "All Folders"}
                    <ChevronDown className="w-3 h-3 opacity-50" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem
                    onClick={() => onSelect(null)}
                    className="flex items-center gap-2"
                >
                    {selectedFolder === null && <Check className="w-4 h-4" />}
                    <span className={selectedFolder === null ? "font-medium" : ""}>
                        All Folders
                    </span>
                </DropdownMenuItem>

                {folders.map((folder) => (
                    <DropdownMenuItem
                        key={folder}
                        onClick={() => onSelect(folder)}
                        className="flex items-center gap-2"
                    >
                        {selectedFolder === folder && <Check className="w-4 h-4" />}
                        <FolderOpen className="w-3 h-3 text-amber-500" />
                        <span className={selectedFolder === folder ? "font-medium" : ""}>
                            {folder}
                        </span>
                    </DropdownMenuItem>
                ))}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
