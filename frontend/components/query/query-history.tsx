"use client";

import { useEffect, useState } from "react";
import { Clock, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

interface QueryHistoryItem {
    query: string;
    timestamp: number;
    workspace_id?: string;
}

const MAX_HISTORY = 10;
const STORAGE_KEY = "query_history";

export function QueryHistory({ onSelectQuery }: { onSelectQuery: (query: string) => void }) {
    const [history, setHistory] = useState<QueryHistoryItem[]>([]);

    useEffect(() => {
        // Load from localStorage on mount
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                setHistory(parsed);
            } catch (e) {
                console.error("Failed to parse query history", e);
            }
        }
    }, []);

    const clearHistory = () => {
        localStorage.removeItem(STORAGE_KEY);
        setHistory([]);
    };

    if (history.length === 0) {
        return null;
    }

    return (
        <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Recent Queries
                </h3>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearHistory}
                    className="h-7 px-2"
                >
                    <Trash2 className="w-3 h-3" />
                </Button>
            </div>

            <ScrollArea className="h-[200px]">
                <div className="space-y-2">
                    {history.map((item, idx) => (
                        <button
                            key={idx}
                            onClick={() => onSelectQuery(item.query)}
                            className="w-full text-left px-3 py-2 text-sm bg-white dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 rounded border border-zinc-200 dark:border-zinc-700 transition-colors"
                        >
                            <p className="truncate">{item.query}</p>
                            <p className="text-xs text-zinc-500 mt-1">
                                {new Date(item.timestamp).toLocaleString()}
                            </p>
                        </button>
                    ))}
                </div>
            </ScrollArea>
        </div>
    );
}

export function addQueryToHistory(query: string, workspace_id?: string) {
    const saved = localStorage.getItem(STORAGE_KEY);
    let history: QueryHistoryItem[] = [];

    if (saved) {
        try {
            history = JSON.parse(saved);
        } catch (e) {
            console.error("Failed to parse query history", e);
        }
    }

    // Add new query to the beginning
    history.unshift({
        query,
        timestamp: Date.now(),
        workspace_id,
    });

    // Keep only MAX_HISTORY items
    history = history.slice(0, MAX_HISTORY);

    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}
