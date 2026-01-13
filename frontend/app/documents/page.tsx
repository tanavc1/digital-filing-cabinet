"use client";

import { useEffect, useState } from "react";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { listDocs } from "@/lib/api";
import { Doc } from "@/lib/types";
import { DocTable } from "@/components/docs/doc-table";
import { UploadButton } from "@/components/docs/upload-button";
import { Loader2 } from "lucide-react";

export default function DocumentsPage() {
    const { workspace, refreshDocs: refreshGlobalDocs } = useWorkspace();
    const [docs, setDocs] = useState<Doc[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchDocs = async () => {
        setLoading(true);
        try {
            const docsList: Doc[] = await listDocs(workspace.id);
            setDocs(docsList);
            // Update global count in sidebar
            refreshGlobalDocs();
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocs();
    }, [workspace.id]);

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
                    <p className="text-sm text-gray-500 mt-1">
                        Manage evidence sources for {workspace.label}.
                    </p>
                </div>
                <UploadButton onUploadComplete={fetchDocs} />
            </div>

            {loading ? (
                <div className="py-12 flex justify-center">
                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                </div>
            ) : (
                <DocTable docs={docs} onDelete={fetchDocs} />
            )}
        </div>
    );
}
