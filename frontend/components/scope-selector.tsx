"use client";

import * as React from "react";
import { Check, ChevronsUpDown, FolderGit2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { Workspace } from "@/lib/types";

interface ScopeSelectorProps {
    workspaces: Workspace[];
    selectedWorkspace: string;
    onSelect: (id: string) => void;
    counts?: Record<string, number>;
}

export function ScopeSelector({ workspaces, selectedWorkspace, onSelect, counts }: ScopeSelectorProps) {
    const [open, setOpen] = React.useState(false);

    const active = workspaces.find((w) => w.id === selectedWorkspace);

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={open}
                    className="w-[200px] justify-between h-9 shadow-sm"
                >
                    <div className="flex items-center gap-2 truncate">
                        <FolderGit2 className="w-4 h-4 text-blue-600" />
                        <span className="truncate">{active ? active.label : "Select Workspace"}</span>
                    </div>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[200px] p-0">
                <Command>
                    <CommandInput placeholder="Search workspace..." />
                    <CommandList>
                        <CommandEmpty>No workspace found.</CommandEmpty>
                        <CommandGroup heading="Available Workspaces">
                            {workspaces.map((framework) => (
                                <CommandItem
                                    key={framework.id}
                                    value={framework.id} // Command uses value for filtering?
                                    keywords={[framework.label]}
                                    onSelect={(currentValue) => {
                                        // currentValue might be normalized by cmdk
                                        // Use the ID directly
                                        onSelect(framework.id);
                                        setOpen(false);
                                    }}
                                >
                                    <Check
                                        className={cn(
                                            "mr-2 h-4 w-4",
                                            selectedWorkspace === framework.id ? "opacity-100" : "opacity-0"
                                        )}
                                    />
                                    <div className="flex flex-1 justify-between items-center">
                                        <span>{framework.label}</span>
                                        {counts && (
                                            <span className="text-xs text-gray-400 ml-2">
                                                {counts[framework.id] ?? 0}
                                            </span>
                                        )}
                                    </div>
                                </CommandItem>
                            ))}
                        </CommandGroup>
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    );
}
