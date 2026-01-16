"use client";

import { useEffect, useState } from "react";
import { getPlaybooks, runPlaybook, getClauseMatrix, Playbook } from "@/lib/api";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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
    Play,
    Loader2,
    Grid3X3,
    CheckCircle,
    AlertTriangle,
    Download
} from "lucide-react";
import Link from "next/link";

interface Evidence {
    file: string;
    page: number;
    snippet: string;
    char_start: number;
    char_end: number;
}

interface MatrixRow {
    doc_id: string;
    doc_title: string;
    clauses: Record<string, {
        id: string;
        value: string;
        status: "resolved" | "needs_review" | "unresolved" | "not_applicable";
        evidence: Evidence[];
        explanation: string;
        snippet: string;
        page_number: number;
        confidence: number;
        verified: boolean;
        flagged: boolean;
    }>;
}

interface MatrixData {
    columns: string[];
    column_labels: Record<string, string>;
    rows: MatrixRow[];
}

export default function ClauseMatrixPage() {
    const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
    const [selectedPlaybook, setSelectedPlaybook] = useState<string>("");
    const [matrix, setMatrix] = useState<MatrixData | null>(null);
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);
    const [runResult, setRunResult] = useState<any>(null);
    const { workspace } = useWorkspace();
    const workspaceId = workspace?.id || "default";

    useEffect(() => {
        loadPlaybooks();
        loadMatrix();
    }, []);

    async function loadPlaybooks() {
        try {
            const data = await getPlaybooks();
            setPlaybooks(data.playbooks || []);
            if (data.playbooks?.length > 0) {
                setSelectedPlaybook(data.playbooks[0].id);
            }
        } catch (err) {
            console.error("Failed to load playbooks:", err);
        }
    }

    async function loadMatrix() {
        try {
            setLoading(true);
            const data = await getClauseMatrix(workspaceId);
            setMatrix(data);
        } catch (err) {
            console.error("Failed to load matrix:", err);
        } finally {
            setLoading(false);
        }
    }

    async function handleRunPlaybook() {
        if (!selectedPlaybook) return;

        try {
            setRunning(true);
            setRunResult(null);
            const result = await runPlaybook(selectedPlaybook, workspaceId);
            setRunResult(result);
            // Reload matrix with new extractions
            await loadMatrix();
        } catch (err) {
            console.error("Playbook run failed:", err);
        } finally {
            setRunning(false);
        }
    }

    function getCellStyle(cell: any) {
        if (!cell) return "bg-gray-50 text-gray-400";

        // Status-based styling for defensible cells
        switch (cell.status) {
            case "resolved":
                return cell.flagged
                    ? "bg-red-50 text-red-800 border-l-4 border-red-500"
                    : "bg-green-50 text-green-800";
            case "needs_review":
                return "bg-amber-50 text-amber-800 border-l-4 border-amber-400";
            case "unresolved":
                return "bg-slate-100 text-slate-600";
            case "not_applicable":
                return "bg-gray-50 text-gray-400";
            default:
                // Legacy fallback
                if (cell.flagged) return "bg-red-50 text-red-800 border-l-4 border-red-500";
                if (cell.verified) return "bg-green-50 text-green-800";
                return "bg-white";
        }
    }

    function getStatusBadge(status: string) {
        switch (status) {
            case "resolved":
                return <span title="Resolved">✅</span>;
            case "needs_review":
                return <span title="Needs Review">⚠️</span>;
            case "unresolved":
                return <span title="Unresolved">❓</span>;
            case "not_applicable":
                return <span title="Not Applicable">➖</span>;
            default:
                return null;
        }
    }

    if (loading && !matrix) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    return (
        <div className="flex h-screen flex-col bg-slate-50/50">
            {/* Header */}
            <header className="flex h-14 items-center justify-between border-b bg-white px-6 shadow-sm">
                <div className="flex items-center gap-2">
                    <Grid3X3 className="h-5 w-5 text-indigo-600" />
                    <h1 className="font-semibold text-lg">Clause Matrix</h1>
                </div>
                <Button variant="outline" size="sm" asChild>
                    <a href={`http://localhost:8000/exports/clause-matrix.csv?workspace_id=${workspaceId}`} download>
                        <Download className="h-4 w-4 mr-2" />
                        Export CSV
                    </a>
                </Button>
            </header>

            <main className="flex-1 overflow-auto p-6 space-y-6">
                {/* Playbook Runner */}
                <Card>
                    <CardHeader>
                        <CardTitle>Run Playbook</CardTitle>
                        <CardDescription>
                            Select a playbook to extract key clauses from matching documents.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex gap-4 items-end">
                            <div className="flex-1 max-w-md">
                                <label className="text-sm font-medium mb-2 block">Playbook</label>
                                <Select value={selectedPlaybook} onValueChange={setSelectedPlaybook}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select playbook" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {playbooks.map((pb) => (
                                            <SelectItem key={pb.id} value={pb.id}>
                                                {pb.name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                {selectedPlaybook && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {playbooks.find(p => p.id === selectedPlaybook)?.description}
                                    </p>
                                )}
                            </div>
                            <Button onClick={handleRunPlaybook} disabled={running || !selectedPlaybook}>
                                {running ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Running...
                                    </>
                                ) : (
                                    <>
                                        <Play className="h-4 w-4 mr-2" />
                                        Run Playbook
                                    </>
                                )}
                            </Button>
                        </div>

                        {/* Run Result */}
                        {runResult && (
                            <div className="mt-4 p-4 bg-indigo-50 rounded-lg">
                                <div className="flex items-center gap-4 text-sm">
                                    <span className="font-medium">{runResult.playbook_name}</span>
                                    <Badge variant="secondary">{runResult.doc_count} docs</Badge>
                                    <Badge variant="secondary">{runResult.extraction_count} clauses</Badge>
                                    {runResult.issue_count > 0 && (
                                        <Badge variant="destructive">{runResult.issue_count} issues</Badge>
                                    )}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Matrix Table */}
                <Card>
                    <CardHeader>
                        <CardTitle>Extraction Matrix</CardTitle>
                        <CardDescription>
                            Click any cell to view evidence details. Red = flagged issue.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="overflow-x-auto">
                        {matrix && matrix.rows.length > 0 ? (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="sticky left-0 bg-white z-10">Document</TableHead>
                                        {matrix.columns.map(col => (
                                            <TableHead key={col} className="text-center min-w-[150px]">
                                                {matrix.column_labels[col] || col}
                                            </TableHead>
                                        ))}
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {matrix.rows.map((row) => (
                                        <TableRow key={row.doc_id}>
                                            <TableCell className="sticky left-0 bg-white font-medium z-10">
                                                <Link href={`/viewer/${row.doc_id}`} className="text-indigo-600 hover:underline">
                                                    {row.doc_title}
                                                </Link>
                                            </TableCell>
                                            {matrix.columns.map(col => {
                                                const cell = row.clauses[col];
                                                return (
                                                    <TableCell key={col} className={`text-center ${getCellStyle(cell)}`}>
                                                        {cell ? (
                                                            <Link
                                                                href={`/evidence/${cell.id}`}
                                                                className="block p-2 hover:bg-gray-100/50 rounded cursor-pointer"
                                                            >
                                                                <div className="flex items-center justify-center gap-1 mb-1">
                                                                    {getStatusBadge(cell.status)}
                                                                    {cell.flagged && <AlertTriangle className="h-3 w-3 text-red-500" />}
                                                                </div>
                                                                <div className="text-xs max-w-[140px] truncate">
                                                                    {cell.status === "resolved" || cell.status === "needs_review"
                                                                        ? (cell.value || "Found")
                                                                        : cell.explanation || "N/A"
                                                                    }
                                                                </div>
                                                                <div className="flex items-center justify-center gap-1 mt-1">
                                                                    {cell.verified && <CheckCircle className="h-3 w-3 text-green-500" />}
                                                                    <span className="text-[10px] text-muted-foreground">
                                                                        {cell.status === "resolved" || cell.status === "needs_review"
                                                                            ? `${Math.round(cell.confidence * 100)}%`
                                                                            : ""
                                                                        }
                                                                    </span>
                                                                </div>
                                                            </Link>
                                                        ) : (
                                                            <span className="text-gray-300" title="No extraction data">—</span>
                                                        )}
                                                    </TableCell>
                                                );
                                            })}
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <div className="text-center py-12 text-muted-foreground">
                                <Grid3X3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                <p>No clause extractions yet. Run a playbook to populate the matrix.</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </main>
        </div>
    );
}
