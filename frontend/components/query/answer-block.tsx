"use client";

import { QueryResult, Doc } from "@/lib/types";
import { AlertTriangle, CheckCircle, ShieldAlert, Download } from "lucide-react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { EvidenceCard } from "./evidence-card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { memo } from "react";

interface AnswerBlockProps {
    result: QueryResult;
    docs: Doc[];
    statusMessage?: string;
    isStreaming?: boolean;
    isTyping?: boolean; // NEW: Visual typing state
}

export const AnswerBlock = memo(function AnswerBlock({ result, docs, statusMessage, isStreaming, isTyping }: AnswerBlockProps) {
    const getDocTitle = (id: string) => docs.find((d) => d.doc_id === id)?.title || "Unknown Doc";

    const handleExportPDF = () => {
        // Create a printable version
        const printWindow = window.open('', '_blank');
        if (!printWindow) return;

        const html = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Query Result Export</title>
                <style>
                    body { font-family: system-ui; padding: 40px; max-width: 800px; margin: 0 auto; }
                    h1 { font-size: 24px; margin-bottom: 20px; }
                    .answer { line-height: 1.6; margin-bottom: 30px; }
                    .evidence { border: 1px solid #ccc; padding: 15px; margin-bottom: 15px; border-radius: 4px; }
                    .quote { background: #f5f5f5; padding: 10px; margin: 10px 0; border-left: 3px solid #007bff; }
                    .source { font-size: 12px; color: #666; margin-top: 10px; }
                </style>
            </head>
            <body>
                <h1>Query Result</h1>
                <div class="answer">
                    <strong>Answer:</strong><br/>
                    ${result.answer.replace(/\n/g, '<br/>')}
                </div>
                ${result.sources && result.sources.length > 0 ? `
                    <h2>Evidence:</h2>
                    ${result.sources.map((s, i) => `
                        <div class="evidence">
                            <div class="quote">${s.quote}</div>
                            <div class="source">Source: ${getDocTitle(s.doc_id)}</div>
                        </div>
                    `).join('')}
                ` : ''}
            </body>
            </html>
        `;

        printWindow.document.write(html);
        printWindow.document.close();
        printWindow.print();
    };

    // Show abstain if: Not streaming AND Not typing AND Abstained
    const isActive = isStreaming || isTyping;

    if (result.abstained && !isActive) {
        return (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
                <Alert variant="destructive" className="bg-red-50 border-red-200 text-red-900">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Not found in the document.</AlertTitle>
                    <AlertDescription className="mt-2 text-sm text-red-800/80">
                        {result.explanation || "No verifiable evidence could be found matching your query."}
                    </AlertDescription>
                </Alert>

                {result.closest_mentions && result.closest_mentions.length > 0 && (
                    <div className="border rounded-md p-4 bg-gray-50">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                            <ShieldAlert className="w-4 h-4" />
                            Closest Mentions (Unverified)
                        </h3>
                        <div className="space-y-3">
                            {result.closest_mentions.map((m, i) => (
                                <div key={i} className="text-sm bg-white p-3 rounded border">
                                    <p className="text-gray-600 mb-2">"...{m.excerpt}..."</p>
                                    <div className="flex justify-between items-center text-xs text-gray-500">
                                        <span>source: {getDocTitle(m.doc_id)}</span>
                                        <Link href={`/viewer/${m.doc_id}`}>
                                            <Button variant="link" size="sm" className="h-5 p-0">Open Doc</Button>
                                        </Link>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
            {/* Answer Region */}
            <div className="bg-white p-6 rounded-lg border shadow-sm relative overflow-hidden transition-all">
                {/* Simple Streaming Spinner/Bar */}
                {isActive && (
                    <div className="absolute top-0 left-0 w-full h-1 bg-blue-50">
                        <div className="h-full bg-blue-500 animate-progress origin-left w-full"></div>
                    </div>
                )}

                <div className="flex items-center justify-between mb-4">
                    {/* Only show header if we have an answer to show */}
                    {result.answer ? (
                        <div className="flex items-center gap-2 text-green-600 text-sm font-medium animate-in fade-in">
                            <CheckCircle className="w-4 h-4" />
                            Verified Answer
                        </div>
                    ) : (
                        <div className="h-5"></div> /* Spacer */
                    )}
                    <div className="flex items-center gap-2">
                        {statusMessage && (
                            <span className="text-xs text-blue-600 font-mono animate-pulse">
                                {statusMessage}
                            </span>
                        )}
                        {result.answer && !isActive && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleExportPDF}
                                className="gap-2 h-7 text-xs"
                            >
                                <Download className="w-3 h-3" />
                                Export PDF
                            </Button>
                        )}
                    </div>
                </div>

                <div className="prose prose-sm max-w-none text-gray-800 min-h-[60px]">
                    {result.answer ? (
                        result.answer.split("\n").map((line, i) => (
                            <p key={i}>{line}</p>
                        ))
                    ) : (
                        <p className="text-gray-400 italic">Thinking...</p>
                    )}
                </div>
            </div>

            {/* Evidence Region - Only show if not active (fully done typing) */}
            {!isActive && result.sources.length > 0 && (
                <div className="pt-4 animate-in fade-in slide-in-from-bottom-2 duration-1000 ease-out fill-mode-forwards">
                    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3 px-1">
                        Supporting Evidence ({result.sources.length})
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {result.sources.map((ev, i) => (
                            <EvidenceCard
                                key={i}
                                evidence={ev}
                                docTitle={getDocTitle(ev.doc_id)}
                            />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
});

