"use client";

import { useEffect, useState } from "react";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { listDocs, deleteDocument, getDocContent } from "@/lib/api";
import { Doc } from "@/lib/types";
import { UploadButton } from "@/components/docs/upload-button";
import { ZipUploadButton } from "@/components/docs/zip-upload-button";
import { Loader2, FileText, Trash2, Search, FolderOpen, Calendar, Clock } from "lucide-react";
import { FileTree } from "@/components/ui/file-tree";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { format } from "date-fns";
import Link from "next/link";

export default function DocumentsPage() {
    const { workspace, refreshDocs: refreshGlobalDocs } = useWorkspace();
    const [docs, setDocs] = useState<Doc[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDoc, setSelectedDoc] = useState<Doc | null>(null);
    const [docContent, setDocContent] = useState<string>("");
    const [loadingContent, setLoadingContent] = useState(false);

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
            setDocContent("");
            await fetchDocs();
        } catch (err) {
            console.error("Delete failed:", err);
            alert("Failed to delete document.");
        }
    };

    const loadDocContent = async (doc: Doc) => {
        setLoadingContent(true);
        try {
            const res = await getDocContent(doc.doc_id, workspace.id);
            setDocContent(res.text || "");
        } catch (err) {
            console.error("Failed to load content:", err);
            setDocContent("Failed to load document content.");
        } finally {
            setLoadingContent(false);
        }
    };

    useEffect(() => {
        fetchDocs();
    }, [workspace.id]);

    useEffect(() => {
        if (selectedDoc) {
            loadDocContent(selectedDoc);
        } else {
            setDocContent("");
        }
    }, [selectedDoc]);

    return (
        <div className="flex flex-col h-screen bg-gray-50 overflow-hidden">
            {/* Header */}
            <header className="bg-white border-b px-6 py-4 flex items-center justify-between shadow-sm flex-shrink-0">
                <div>
                    <h1 className="text-xl font-bold text-gray-900">Document Library</h1>
                    <p className="text-xs text-gray-500">
                        {workspace.label} • {docs.length} document{docs.length !== 1 ? 's' : ''}
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
                            Files
                        </h2>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2">
                        {loading ? (
                            <div className="flex justify-center p-8">
                                <Loader2 className="w-6 h-6 animate-spin text-gray-300" />
                            </div>
                        ) : docs.length === 0 ? (
                            <div className="flex flex-col items-center justify-center p-8 text-gray-400">
                                <FolderOpen className="w-12 h-12 mb-3 stroke-1" />
                                <p className="text-sm">No documents yet</p>
                                <p className="text-xs">Upload files to get started</p>
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

                {/* Right: Document Preview */}
                <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
                    {selectedDoc ? (
                        <div className="max-w-4xl mx-auto space-y-4">
                            {/* Document Header */}
                            <Card>
                                <CardHeader className="pb-3">
                                    <div className="flex items-start justify-between">
                                        <div className="space-y-1">
                                            <CardTitle className="text-lg flex items-center gap-2">
                                                <FileText className="w-5 h-5 text-indigo-500" />
                                                {selectedDoc.title}
                                            </CardTitle>
                                            <div className="flex items-center gap-4 text-xs text-gray-500">
                                                <span className="flex items-center gap-1">
                                                    <Calendar className="w-3 h-3" />
                                                    {format(new Date(selectedDoc.created_at * 1000), "MMM d, yyyy")}
                                                </span>
                                                <span className="flex items-center gap-1">
                                                    <FolderOpen className="w-3 h-3" />
                                                    {selectedDoc.folder_path || "/"}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <Button variant="outline" size="sm" asChild>
                                                <Link href={`/?q=&doc=${selectedDoc.doc_id}`}>
                                                    <Search className="w-3 h-3 mr-1" />
                                                    Search
                                                </Link>
                                            </Button>
                                            <Button
                                                variant="destructive"
                                                size="sm"
                                                onClick={() => handleDelete(selectedDoc.doc_id)}
                                            >
                                                <Trash2 className="w-3 h-3 mr-1" />
                                                Delete
                                            </Button>
                                        </div>
                                    </div>
                                </CardHeader>
                            </Card>

                            {/* Document Content Preview */}
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm font-medium text-gray-600">
                                        Document Preview
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    {loadingContent ? (
                                        <div className="flex justify-center py-8">
                                            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                                        </div>
                                    ) : (
                                        <div className="prose prose-sm max-w-none">
                                            <pre className="whitespace-pre-wrap text-xs text-gray-700 bg-gray-50 p-4 rounded-lg max-h-[500px] overflow-y-auto font-mono">
                                                {docContent || "No content available."}
                                            </pre>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
                            <FileText className="w-16 h-16 stroke-1 opacity-50" />
                            <p className="text-sm">Select a document to preview</p>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
