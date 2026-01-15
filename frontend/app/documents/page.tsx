"use client";

import { useEffect, useState } from "react";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { listDocs, deleteDocument } from "@/lib/api";
import { Doc } from "@/lib/types";
import { UploadButton } from "@/components/docs/upload-button";
import { ZipUploadButton } from "@/components/docs/zip-upload-button";
import { Loader2, FileText, AlertTriangle, ShieldCheck, Tag, Trash2, Eye } from "lucide-react";
import { FileTree } from "@/components/ui/file-tree";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { format } from "date-fns";
import Link from "next/link";

export default function DocumentsPage() {
    const { workspace, refreshDocs: refreshGlobalDocs } = useWorkspace();
    const [docs, setDocs] = useState<Doc[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDoc, setSelectedDoc] = useState<Doc | null>(null);

    const fetchDocs = async () => {
        setLoading(true);
        try {
            const docsList: Doc[] = await listDocs(workspace.id);
            setDocs(docsList);
            refreshGlobalDocs();
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (docId: string) => {
        if (!confirm("Delete this document? This cannot be undone.")) return;
        try {
            await deleteDocument(docId, workspace.id);
            setSelectedDoc(null);
            await fetchDocs();
        } catch (err) {
            console.error("Delete failed:", err);
            alert("Failed to delete document.");
        }
    };

    useEffect(() => {
        fetchDocs();
    }, [workspace.id]);

    const getRiskColor = (level?: string) => {
        switch (level) {
            case "High": return "destructive";
            case "Medium": return "warning"; // Need to ensure variant exists or use custom className
            case "Low": return "secondary";
            case "Clean": return "success"; // Need variant
            default: return "outline";
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50 overflow-hidden">
            {/* Header */}
            <header className="bg-white border-b px-6 py-4 flex items-center justify-between shadow-sm flex-shrink-0">
                <div>
                    <h1 className="text-xl font-bold text-gray-900">Virtual Data Room</h1>
                    <p className="text-xs text-gray-500">
                        {workspace.label} • {docs.length} Documents
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <ZipUploadButton onUploadComplete={fetchDocs} />
                    <UploadButton onUploadComplete={fetchDocs} />
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 flex overflow-hidden">
                {/* Left: File Tree */}
                <div className="w-1/3 min-w-[300px] border-r bg-white flex flex-col">
                    <div className="p-3 border-b bg-gray-50/50">
                        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            Directory
                        </h2>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2">
                        {loading ? (
                            <div className="flex justify-center p-8">
                                <Loader2 className="w-6 h-6 animate-spin text-gray-300" />
                            </div>
                        ) : (
                            <FileTree
                                docs={docs}
                                onSelectDoc={setSelectedDoc}
                                selectedDocId={selectedDoc?.doc_id}
                            />
                        )}
                    </div>
                </div>

                {/* Right: Document Detils */}
                <div className="flex-1 overflow-y-auto p-8 bg-gray-50/50">
                    {selectedDoc ? (
                        <div className="max-w-3xl mx-auto space-y-6">

                            {/* Title Card */}
                            <Card>
                                <CardHeader>
                                    <div className="flex items-start justify-between">
                                        <div className="space-y-1">
                                            <CardTitle className="text-xl flex items-center gap-2">
                                                <FileText className="w-5 h-5 text-blue-600" />
                                                {selectedDoc.title}
                                            </CardTitle>
                                            <CardDescription className="text-xs font-mono text-gray-400">
                                                ID: {selectedDoc.doc_id}
                                            </CardDescription>
                                        </div>
                                        <Badge variant="outline" className="text-xs">
                                            {format(new Date(selectedDoc.created_at * 1000), "MMM d, yyyy")}
                                        </Badge>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex gap-4">
                                        <div className="space-y-1">
                                            <span className="text-xs font-medium text-gray-500">Doc Type</span>
                                            <div className="flex items-center gap-1.5 border rounded px-2 py-1 bg-gray-50">
                                                <Tag className="w-3 h-3 text-gray-400" />
                                                <span className="text-sm font-medium">{selectedDoc.doc_type || "Unclassified"}</span>
                                            </div>
                                        </div>
                                        <div className="space-y-1">
                                            <span className="text-xs font-medium text-gray-500">Risk Level</span>
                                            <div className="flex items-center gap-1.5 border rounded px-2 py-1 bg-gray-50">
                                                <AlertTriangle className={`w-3 h-3 ${selectedDoc.risk_level === 'High' ? 'text-red-500' : 'text-gray-400'}`} />
                                                <span className="text-sm font-medium">{selectedDoc.risk_level || "Unknown"}</span>
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Actions */}
                            <div className="flex gap-2">
                                <Button asChild variant="outline">
                                    <Link href={`/viewer/${selectedDoc.doc_id}?workspace_id=${workspace.id}`}>
                                        <Eye className="h-4 w-4 mr-2" />
                                        View Full Document
                                    </Link>
                                </Button>
                                <Button variant="destructive" onClick={() => handleDelete(selectedDoc.doc_id)}>
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    Delete
                                </Button>
                            </div>

                            {/* Summary / Analysis */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-base flex items-center gap-2">
                                        <ShieldCheck className="w-4 h-4 text-green-600" />
                                        AI Summary & Analysis
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="prose prose-sm max-w-none text-gray-600">
                                        {selectedDoc.summary_text ? (
                                            <p className="whitespace-pre-wrap">{selectedDoc.summary_text}</p>
                                        ) : (
                                            <p className="italic text-gray-400">No summary available.</p>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Location */}
                            <div className="text-xs text-gray-400 font-mono">
                                Path: {selectedDoc.folder_path || "/"}{selectedDoc.title}
                            </div>

                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4 opacity-50">
                            <FileText className="w-16 h-16 stroke-[1.5]" />
                            <p>Select a document from the Data Room to view analysis.</p>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
