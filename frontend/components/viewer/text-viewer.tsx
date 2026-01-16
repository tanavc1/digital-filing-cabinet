"use client";

import { useEffect, useRef, useMemo } from "react";
import { cn } from "@/lib/utils";

interface TextViewerProps {
    text: string;
    highlight?: { start: number; end: number };
}

export function TextViewer({ text, highlight }: TextViewerProps) {
    const highlightRef = useRef<HTMLSpanElement>(null);

    // Scroll to highlight on mount
    useEffect(() => {
        if (highlight && highlightRef.current) {
            highlightRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }, [highlight]);

    // Split text into [before, match, after]
    const content = useMemo(() => {
        if (!highlight) return <>{text}</>;

        const { start, end } = highlight;
        if (start < 0 || end > text.length || start >= end) {
            return <>{text}</>; // Invalid range fallback
        }

        const before = text.substring(0, start);
        const match = text.substring(start, end);
        const after = text.substring(end);

        return (
            <>
                {before}
                <span
                    ref={highlightRef}
                    className="bg-yellow-200 text-gray-900 border-b-2 border-yellow-500"
                >
                    {match}
                </span>
                {after}
            </>
        );
    }, [text, highlight]);

    return (
        <div className="bg-white p-6 font-mono text-sm leading-relaxed whitespace-pre-wrap break-words max-w-full text-gray-800">
            {content}
        </div>
    );
}
