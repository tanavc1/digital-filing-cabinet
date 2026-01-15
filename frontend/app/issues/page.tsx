"use client";

import { useEffect, useState } from "react";
import { getIssues, updateIssue, deleteIssue, Issue } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    AlertTriangle,
    AlertCircle,
    Info,
    Loader2,
    Download,
    Trash2,
    ExternalLink
} from "lucide-react";
import Link from "next/link";

export default function IssuesPage() {
    const [issues, setIssues] = useState<Issue[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterSeverity, setFilterSeverity] = useState<string>("all");
    const [filterStatus, setFilterStatus] = useState<string>("all");

    useEffect(() => {
        loadIssues();
    }, [filterSeverity, filterStatus]);

    async function loadIssues() {
        try {
            setLoading(true);
            const filters: any = {};
            if (filterSeverity !== "all") filters.severity = filterSeverity;
            if (filterStatus !== "all") filters.status = filterStatus;
            const data = await getIssues(Object.keys(filters).length > 0 ? filters : undefined);
            setIssues(data.issues || []);
        } catch (err) {
            console.error("Failed to load issues:", err);
        } finally {
            setLoading(false);
        }
    }

    async function handleStatusChange(issueId: string, status: string) {
        await updateIssue(issueId, { status });
        loadIssues();
    }

    async function handleDelete(issueId: string) {
        if (confirm("Delete this issue?")) {
            await deleteIssue(issueId);
            loadIssues();
        }
    }

    function getSeverityIcon(severity: string) {
        switch (severity) {
            case "critical":
                return <AlertTriangle className="h-5 w-5 text-red-500" />;
            case "warning":
                return <AlertCircle className="h-5 w-5 text-amber-500" />;
            default:
                return <Info className="h-5 w-5 text-blue-500" />;
        }
    }

    function getSeverityBadge(severity: string) {
        switch (severity) {
            case "critical":
                return <Badge variant="destructive">Critical</Badge>;
            case "warning":
                return <Badge className="bg-amber-500">Warning</Badge>;
            default:
                return <Badge className="bg-blue-500">Info</Badge>;
        }
    }

    function getStatusBadge(status: string) {
        switch (status) {
            case "open":
                return <Badge variant="outline" className="border-red-300 text-red-600">Open</Badge>;
            case "in_progress":
                return <Badge variant="outline" className="border-amber-300 text-amber-600">In Progress</Badge>;
            case "resolved":
                return <Badge variant="outline" className="border-green-300 text-green-600">Resolved</Badge>;
            default:
                return <Badge variant="secondary">{status}</Badge>;
        }
    }

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    const criticalCount = issues.filter(i => i.severity === "critical").length;
    const openCount = issues.filter(i => i.status === "open").length;

    return (
        <div className="flex h-screen flex-col bg-slate-50/50">
            {/* Header */}
            <header className="flex h-14 items-center justify-between border-b bg-white px-6 shadow-sm">
                <div className="flex items-center gap-3">
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                    <h1 className="font-semibold text-lg">Issues</h1>
                    {criticalCount > 0 && (
                        <Badge variant="destructive">{criticalCount} critical</Badge>
                    )}
                    {openCount > 0 && (
                        <Badge variant="secondary">{openCount} open</Badge>
                    )}
                </div>
                <Button variant="outline" size="sm" asChild>
                    <a href="http://localhost:8000/exports/issues.csv" download>
                        <Download className="h-4 w-4 mr-2" />
                        Export CSV
                    </a>
                </Button>
            </header>

            <main className="flex-1 overflow-auto p-6 space-y-4">
                {/* Filters */}
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-4">
                            <Select value={filterSeverity} onValueChange={setFilterSeverity}>
                                <SelectTrigger className="w-32">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Severity</SelectItem>
                                    <SelectItem value="critical">Critical</SelectItem>
                                    <SelectItem value="warning">Warning</SelectItem>
                                    <SelectItem value="info">Info</SelectItem>
                                </SelectContent>
                            </Select>
                            <Select value={filterStatus} onValueChange={setFilterStatus}>
                                <SelectTrigger className="w-32">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Status</SelectItem>
                                    <SelectItem value="open">Open</SelectItem>
                                    <SelectItem value="in_progress">In Progress</SelectItem>
                                    <SelectItem value="resolved">Resolved</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </CardContent>
                </Card>

                {/* Issues Table */}
                <Card>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-12"></TableHead>
                                <TableHead>Issue</TableHead>
                                <TableHead>Document</TableHead>
                                <TableHead>Owner</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Action Required</TableHead>
                                <TableHead className="w-20"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {issues.map((issue) => (
                                <TableRow key={issue.id} className="hover:bg-slate-50">
                                    <TableCell>
                                        {getSeverityIcon(issue.severity)}
                                    </TableCell>
                                    <TableCell>
                                        <div className="space-y-1">
                                            <div className="font-medium">{issue.title}</div>
                                            {issue.description && (
                                                <div className="text-xs text-muted-foreground max-w-md truncate">
                                                    {issue.description}
                                                </div>
                                            )}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        {issue.doc_id ? (
                                            <Link
                                                href={issue.clause_id ? `/evidence/${issue.clause_id}` : `/viewer/${issue.doc_id}`}
                                                className="text-indigo-600 hover:underline flex items-center gap-1"
                                            >
                                                {issue.doc_title || "View"}
                                                <ExternalLink className="h-3 w-3" />
                                            </Link>
                                        ) : (
                                            <span className="text-muted-foreground">—</span>
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        {issue.owner || <span className="text-muted-foreground">Unassigned</span>}
                                    </TableCell>
                                    <TableCell>
                                        <Select
                                            value={issue.status}
                                            onValueChange={(val) => handleStatusChange(issue.id, val)}
                                        >
                                            <SelectTrigger className="w-32 h-8">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="open">Open</SelectItem>
                                                <SelectItem value="in_progress">In Progress</SelectItem>
                                                <SelectItem value="resolved">Resolved</SelectItem>
                                                <SelectItem value="wont_fix">Won't Fix</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </TableCell>
                                    <TableCell className="text-sm max-w-xs truncate">
                                        {issue.action_required || <span className="text-muted-foreground">—</span>}
                                    </TableCell>
                                    <TableCell>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => handleDelete(issue.id)}
                                            className="text-muted-foreground hover:text-red-500"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>

                    {issues.length === 0 && (
                        <div className="text-center py-12 text-muted-foreground">
                            <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                            <p>No issues found. Run a playbook to detect issues automatically.</p>
                        </div>
                    )}
                </Card>
            </main>
        </div>
    );
}
