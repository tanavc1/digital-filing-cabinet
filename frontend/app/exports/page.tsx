"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    Download,
    FileSpreadsheet,
    PackageCheck,
    Loader2,
    CheckCircle2,
    FileText,
    AlertTriangle
} from "lucide-react";
import { useWorkspace } from "@/components/providers/workspace-provider";

export default function ExportsPage() {
    const { workspace } = useWorkspace();
    const [stats, setStats] = useState<any>(null);

    useEffect(() => {
        // Fetch project stats to show readiness
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/project/stats?workspace_id=${workspace.id}`)
            .then(res => res.json())
            .then(setStats)
            .catch(err => console.error(err));
    }, [workspace.id]);

    const handleExport = (type: string) => {
        const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/exports/excel/${type}?workspace_id=${workspace.id}`;
        window.open(url, '_blank');
    };

    return (
        <div className="flex flex-col h-screen bg-slate-50">
            {/* Header */}
            <div className="bg-white border-b px-6 py-6">
                <div className="max-w-4xl mx-auto">
                    <h1 className="text-2xl font-bold flex items-center gap-2 text-indigo-900">
                        <PackageCheck className="text-indigo-600" />
                        Delivery Center
                    </h1>
                    <p className="text-gray-500">Generate final deliverables for the client.</p>
                </div>
            </div>

            <div className="flex-1 overflow-auto p-8">
                <div className="max-w-4xl mx-auto space-y-8">
                    {/* Status Overview */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <Card className="bg-green-50 border-green-200">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-green-700">Project Completion</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-green-800">
                                    {stats ? Math.round(stats.completion_percentage) : 0}%
                                </div>
                                <p className="text-xs text-green-600">Based on review status</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">QA Approved</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{stats?.qa_approved || 0}</div>
                                <p className="text-xs text-gray-400">Documents ready for pack</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">Flagged Issues</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-amber-600">{stats?.flagged || 0}</div>
                                <p className="text-xs text-gray-400">Require resolution before export</p>
                            </CardContent>
                        </Card>
                    </div>

                    <h2 className="text-lg font-semibold text-gray-800">Available Exports</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Clause Matrix */}
                        <Card className="hover:shadow-md transition-shadow">
                            <CardHeader>
                                <div className="flex justify-between items-start">
                                    <div className="p-2 bg-green-100 rounded-lg">
                                        <FileSpreadsheet className="w-6 h-6 text-green-600" />
                                    </div>
                                    <Badge variant="secondary">XLSX</Badge>
                                </div>
                                <CardTitle className="mt-4">Clause Matrix</CardTitle>
                                <CardDescription>Full grid of extracted clauses across all documents.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ul className="text-sm text-gray-500 space-y-2 mb-6">
                                    <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-500" /> Includes snippets & confidence</li>
                                    <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-500" /> Grouped by Document</li>
                                </ul>
                                <Button className="w-full" onClick={() => handleExport('clause_matrix')}>
                                    <Download className="w-4 h-4 mr-2" /> Download Matrix
                                </Button>
                            </CardContent>
                        </Card>

                        {/* Issues Register */}
                        <Card className="hover:shadow-md transition-shadow">
                            <CardHeader>
                                <div className="flex justify-between items-start">
                                    <div className="p-2 bg-red-100 rounded-lg">
                                        <AlertTriangle className="w-6 h-6 text-red-600" />
                                    </div>
                                    <Badge variant="secondary">XLSX</Badge>
                                </div>
                                <CardTitle className="mt-4">Issues Register</CardTitle>
                                <CardDescription>Consolidated list of all flagged risks and issues.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ul className="text-sm text-gray-500 space-y-2 mb-6">
                                    <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-500" /> Sorted by Severity</li>
                                    <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-500" /> Includes Action Items</li>
                                </ul>
                                <Button className="w-full" variant="outline" onClick={() => handleExport('issues_list')}>
                                    <Download className="w-4 h-4 mr-2" /> Download Register
                                </Button>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    );
}
