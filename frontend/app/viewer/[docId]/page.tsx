"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { getDocContent } from "@/lib/api";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { TextViewer } from "@/components/viewer/text-viewer";
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function ViewerPage() {
    const { docId } = useParams();
    const searchParams = useSearchParams();
    const { workspace } = useWorkspace();
    const [text, setText] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    // Parse highlight param: ?highlight=10,20
    const highlightParam = searchParams.get("highlight");
    const highlight = highlightParam
        ? {
            start: parseInt(highlightParam.split(",")[0]),
            end: parseInt(highlightParam.split(",")[1]),
        }
        : undefined;

    useEffect(() => {
        if (docId) {
            setLoading(true);
            getDocContent(docId as string, workspace.id)
                .then((res) => setText(res.text))
                .catch((err) => {
                    console.error(err);
                    setText("Error loading document. Please ensure it was ingested with full text support.");
                })
                .finally(() => setLoading(false));
        }
    }, [docId, workspace.id]);

    return (
        <div className="flex flex-col h-screen">
            {/* Header */}
            <div className="border-b bg-white p-4 flex items-center justify-between sticky top-0 z-10 shadow-sm">
                <div className="flex items-center gap-4">
                    <Link href="/documents">
                        <Button variant="ghost" size="sm" className="gap-2">
                            <ArrowLeft className="w-4 h-4" />
                            Back to Documents
                        </Button>
                    </Link>
                    <div className="h-6 w-px bg-gray-200" />
                    <span className="font-medium text-sm text-gray-700">Document ID: {docId}</span>
                </div>
                {highlight && (
                    <div className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                        Highlighting offsets: {highlight.start}-{highlight.end}
                    </div>
                )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto bg-gray-50">
                <div className="max-w-4xl mx-auto my-8 shadow-sm">
                    {loading ? (
                        <div className="flex justify-center py-20">
                            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                        </div>
                    ) : (
                        <TextViewer text={text || ""} highlight={highlight} />
                    )}
                </div>
            </div>
        </div>
    );
}
