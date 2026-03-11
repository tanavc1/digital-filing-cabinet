"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, FileText, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TextViewer } from "@/components/viewer/text-viewer";
import { useWorkspace } from "@/components/providers/workspace-provider";
import api from "@/lib/api";
import Link from "next/link";

export default function DocumentViewerPage() {
    const params = useParams();
    const searchParams = useSearchParams();
    const { workspace, docs } = useWorkspace();

    const docId = params.doc_id as string;
    const workspaceId = searchParams.get("workspace_id") || workspace?.id || "default";
    const quoteParam = searchParams.get("quote");

    const [text, setText] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Get document title from workspace docs
    const docTitle = docs?.find((d) => d.doc_id === docId)?.title || docId;

    useEffect(() => {
        async function fetchContent() {
            try {
                setLoading(true);
                setError(null);
                const res = await api.get(`/documents/${encodeURIComponent(docId)}/content`, {
                    params: { workspace_id: workspaceId },
                });
                setText(res.data.text);
            } catch (err: any) {
                console.error("Failed to fetch document content:", err);
                if (err.response?.status === 404) {
                    setError("Document not found. It may have been deleted.");
                } else {
                    setError("Failed to load document content.");
                }
            } finally {
                setLoading(false);
            }
        }

        if (docId) {
            fetchContent();
        }
    }, [docId, workspaceId]);

    // Find the most relevant portion of the quote in the document
    const highlight = useMemo(() => {
        if (!text || !quoteParam) return undefined;

        const quote = decodeURIComponent(quoteParam);
        const textLower = text.toLowerCase();

        // Try exact match first
        let start = textLower.indexOf(quote.toLowerCase());
        if (start !== -1) {
            return { start, end: start + quote.length };
        }

        // Extract key phrases from the quote to search for
        // Look for the most specific/longest phrase that exists in the document
        const phrases = [
            // Try finding key value phrases (e.g., "9 months base salary")
            quote.match(/\d+\s*months?\s*base\s*salary[^,]*/i)?.[0],
            // Try finding amounts
            quote.match(/\$[\d,]+/)?.[0],
            // Try finding "Severance:" section
            "Severance:",
            // Try finding names
            quote.match(/[A-Z][a-z]+\s+[A-Z][a-z]+/)?.[0],
        ].filter(Boolean) as string[];

        // Find the best matching phrase
        for (const phrase of phrases) {
            const idx = textLower.indexOf(phrase.toLowerCase());
            if (idx !== -1) {
                // Expand to include the full line(s) containing this phrase
                let lineStart = text.lastIndexOf('\n', idx);
                if (lineStart === -1) lineStart = 0;
                else lineStart += 1;

                let lineEnd = text.indexOf('\n', idx + phrase.length);
                if (lineEnd === -1) lineEnd = text.length;

                return { start: lineStart, end: lineEnd };
            }
        }

        // Last resort: find any word from the quote (prioritize longer words)
        const words = quote.split(/\s+/).filter(w => w.length > 5).sort((a, b) => b.length - a.length);
        for (const word of words) {
            const idx = textLower.indexOf(word.toLowerCase());
            if (idx !== -1) {
                // Expand to full line
                let lineStart = text.lastIndexOf('\n', idx);
                if (lineStart === -1) lineStart = 0;
                else lineStart += 1;

                let lineEnd = text.indexOf('\n', idx + word.length);
                if (lineEnd === -1) lineEnd = text.length;

                return { start: lineStart, end: lineEnd };
            }
        }

        return undefined;
    }, [text, quoteParam]);

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-6 flex items-center gap-4">
                    <Button variant="ghost" size="sm" asChild>
                        <Link href="/">
                            <ArrowLeft className="w-4 h-4 mr-1" />
                            Back to Search
                        </Link>
                    </Button>
                </div>

                <Card>
                    <CardHeader className="border-b">
                        <CardTitle className="flex items-center gap-2">
                            <FileText className="w-5 h-5 text-indigo-500" />
                            {docTitle}
                        </CardTitle>
                        {highlight && (
                            <p className="text-sm text-green-600 mt-1 font-medium">
                                ✓ Evidence found and highlighted below
                            </p>
                        )}
                        {quoteParam && !highlight && text && (
                            <p className="text-sm text-amber-600 mt-1">
                                ⚠ Could not locate exact quote in document
                            </p>
                        )}
                    </CardHeader>

                    <CardContent className="p-0">
                        {loading && (
                            <div className="flex items-center justify-center h-64">
                                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                            </div>
                        )}

                        {error && (
                            <div className="flex flex-col items-center justify-center h-64 text-red-500 gap-2">
                                <AlertCircle className="w-8 h-8" />
                                <p>{error}</p>
                            </div>
                        )}

                        {!loading && !error && text && (
                            <TextViewer text={text} highlight={highlight} />
                        )}

                        {!loading && !error && !text && (
                            <div className="flex items-center justify-center h-64 text-gray-400">
                                <p>No content available for this document.</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
