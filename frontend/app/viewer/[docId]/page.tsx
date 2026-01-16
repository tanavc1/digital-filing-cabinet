"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { getDocContent } from "@/lib/api";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { TextViewer } from "@/components/viewer/text-viewer";
import { Loader2, ArrowLeft, Plus, AlertTriangle, CheckCircle2, ChevronRight, Gavel } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

export default function ViewerPage() {
    const { docId } = useParams();
    const searchParams = useSearchParams();
    const { workspace } = useWorkspace();
    const [text, setText] = useState<string | null>(null);
    const [analysis, setAnalysis] = useState<{ clauses: any[], issues: any[] } | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState("clauses");

    // Parse highlight param
    const highlightParam = searchParams.get("highlight");
    const highlight = highlightParam
        ? {
            start: parseInt(highlightParam.split(",")[0]),
            end: parseInt(highlightParam.split(",")[1]),
        }
        : undefined;

    const wsParam = searchParams.get("workspace_id");
    const effectiveWorkspace = wsParam || workspace.id || "default";

    useEffect(() => {
        if (docId) {
            setLoading(true);
            Promise.all([
                getDocContent(docId as string, effectiveWorkspace),
                fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/documents/${docId}/analysis?workspace_id=${effectiveWorkspace}`).then(r => r.json())
            ])
                .then(([docRes, analysisRes]) => {
                    setText(docRes.text);
                    setAnalysis(analysisRes);
                })
                .catch((err) => {
                    console.error(err);
                    setText("Error loading document.");
                })
                .finally(() => setLoading(false));
        }
    }, [docId, effectiveWorkspace]);

    return (
        <div className="flex flex-col h-screen bg-slate-50">
            {/* Header */}
            <header className="h-14 border-b bg-white flex items-center justify-between px-4 sticky top-0 z-20 shadow-sm">
                <div className="flex items-center gap-4">
                    <Link href="/documents">
                        <Button variant="ghost" size="sm" className="gap-2 text-gray-600">
                            <ArrowLeft className="w-4 h-4" />
                            Back
                        </Button>
                    </Link>
                    <div className="h-4 w-px bg-gray-200" />
                    <span className="font-medium text-sm text-gray-900">Document Review</span>
                    <Badge variant="outline" className="font-mono text-xs">{docId}</Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm">Previous</Button>
                    <Button variant="outline" size="sm">Next</Button>
                    <div className="h-4 w-px bg-gray-200 mx-2" />
                    <Button size="sm" className="bg-green-600 hover:bg-green-700">Complete Review</Button>
                </div>
            </header>

            {/* Split View */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Panel: Document */}
                <div className="flex-1 bg-gray-100 overflow-auto relative flex justify-center p-4">
                    <div className="bg-white shadow-lg w-full max-w-4xl rounded-lg">
                        {loading ? (
                            <div className="flex items-center justify-center h-64">
                                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                            </div>
                        ) : (
                            <TextViewer text={text || ""} highlight={highlight} />
                        )}
                    </div>
                </div>

                {/* Right Panel: Analysis */}
                <div className="w-[400px] border-l bg-white flex flex-col shadow-xl z-10">
                    <Tabs defaultValue="clauses" className="flex-1 flex flex-col" onValueChange={setActiveTab}>
                        <div className="px-4 py-3 border-b bg-gray-50/50">
                            <TabsList className="w-full grid grid-cols-2">
                                <TabsTrigger value="clauses" className="gap-2">
                                    <Gavel className="w-4 h-4" /> Clauses
                                    <Badge variant="secondary" className="ml-1 text-xs">{analysis?.clauses?.length || 0}</Badge>
                                </TabsTrigger>
                                <TabsTrigger value="issues" className="gap-2">
                                    <AlertTriangle className="w-4 h-4" /> Issues
                                    <Badge variant="secondary" className="ml-1 text-xs">{analysis?.issues?.length || 0}</Badge>
                                </TabsTrigger>
                            </TabsList>
                        </div>

                        <ScrollArea className="flex-1">
                            <TabsContent value="clauses" className="p-4 space-y-4 mt-0">
                                {analysis?.clauses?.map((clause: any) => (
                                    <Card key={clause.id} className="group hover:border-indigo-300 transition-colors cursor-pointer">
                                        <CardHeader className="p-3 pb-2 space-y-0">
                                            <div className="flex justify-between items-start">
                                                <Badge variant="outline" className="uppercase text-[10px] tracking-wider text-indigo-600 border-indigo-100 bg-indigo-50">
                                                    {clause.clause_type}
                                                </Badge>
                                                {clause.confidence > 0.8 && <CheckCircle2 className="w-3 h-3 text-green-500" />}
                                            </div>
                                        </CardHeader>
                                        <CardContent className="p-3 pt-2 text-sm">
                                            <p className="font-medium text-gray-900 mb-1 break-words">{clause.extracted_value}</p>
                                            <p className="text-gray-500 line-clamp-3 text-xs italic">
                                                "{clause.snippet}"
                                            </p>
                                            <div className="mt-2 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Button variant="ghost" size="sm" className="h-6 text-xs">View context <ChevronRight className="w-3 h-3 ml-1" /></Button>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                                {!analysis?.clauses?.length && (
                                    <div className="text-center py-12 text-muted-foreground text-sm">
                                        No clauses extracted. Run a playbook?
                                    </div>
                                )}
                            </TabsContent>

                            <TabsContent value="issues" className="p-4 space-y-4 mt-0">
                                <Button className="w-full gap-2" variant="outline" size="sm">
                                    <Plus className="w-4 h-4" /> Add Issue
                                </Button>
                                {analysis?.issues?.map((issue: any) => (
                                    <Card key={issue.id} className="border-l-4 border-l-red-500">
                                        <CardHeader className="p-3 pb-1">
                                            <div className="flex justify-between">
                                                <h4 className="font-semibold text-sm">{issue.title}</h4>
                                                <Badge variant={issue.severity === 'critical' ? 'destructive' : 'secondary'} className="capitalize text-[10px]">
                                                    {issue.severity}
                                                </Badge>
                                            </div>
                                        </CardHeader>
                                        <CardContent className="p-3 pt-2 text-sm text-gray-600">
                                            <p className="mb-2">{issue.description}</p>
                                            {issue.action_required && (
                                                <div className="bg-red-50 text-red-700 text-xs p-2 rounded flex items-start gap-2">
                                                    <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                                                    {issue.action_required}
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>
                                ))}
                                {!analysis?.issues?.length && (
                                    <div className="text-center py-12 text-muted-foreground text-sm">
                                        No issues flagged yet.
                                    </div>
                                )}
                            </TabsContent>
                        </ScrollArea>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}
