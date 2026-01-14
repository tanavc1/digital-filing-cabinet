"use client";

import { useState, useEffect } from "react";
import { useWorkspace } from "@/components/providers/workspace-provider";
import {
    listAuditTemplates,
    runAudit,
    AuditTemplate,
    AuditResult,
    AuditFinding
} from "@/lib/api";
import { FolderFilter } from "@/components/folder-filter";
import { Button } from "@/components/ui/button";
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
    Shield,
    AlertTriangle,
    CheckCircle,
    HelpCircle,
    XCircle,
    Loader2,
    FileDown,
    Play
} from "lucide-react";
import { toast } from "sonner";

// Severity badge styling
const severityConfig = {
    HIGH: { color: "bg-red-100 text-red-700", icon: AlertTriangle },
    MEDIUM: { color: "bg-yellow-100 text-yellow-700", icon: AlertTriangle },
    LOW: { color: "bg-blue-100 text-blue-700", icon: Shield },
    INFO: { color: "bg-gray-100 text-gray-600", icon: Shield },
};

// Status badge styling
const statusConfig = {
    FOUND: { color: "bg-green-100 text-green-700", icon: CheckCircle, label: "Found" },
    NOT_FOUND: { color: "bg-gray-100 text-gray-500", icon: XCircle, label: "Not Found" },
    UNCLEAR: { color: "bg-yellow-100 text-yellow-600", icon: HelpCircle, label: "Unclear" },
    ERROR: { color: "bg-red-100 text-red-600", icon: XCircle, label: "Error" },
};

export default function AuditPage() {
    const { workspace, docs } = useWorkspace();

    // State
    const [templates, setTemplates] = useState<AuditTemplate[]>([]);
    const [selectedTemplate, setSelectedTemplate] = useState<string>("");
    const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
    const [isRunning, setIsRunning] = useState(false);
    const [result, setResult] = useState<AuditResult | null>(null);

    // Load templates on mount
    useEffect(() => {
        listAuditTemplates().then(setTemplates).catch(console.error);
    }, []);

    // Run audit
    const handleRunAudit = async () => {
        if (!selectedTemplate) {
            toast.error("Please select an audit template");
            return;
        }

        setIsRunning(true);
        setResult(null);
        toast.info("Running audit... This may take a few minutes.");

        try {
            const auditResult = await runAudit(
                workspace.id,
                selectedTemplate,
                selectedFolder
            );
            setResult(auditResult);
            toast.success(`Audit complete! Found ${auditResult.summary.found} items, ${auditResult.summary.high_risk} high risk.`);
        } catch (err: any) {
            console.error("Audit failed:", err);
            toast.error(err?.response?.data?.detail || "Audit failed");
        } finally {
            setIsRunning(false);
        }
    };

    // Export to CSV
    const handleExport = () => {
        if (!result) return;

        const csvHeader = "Question,Answer,Status,Severity,Category,Citations\n";
        const csvRows = result.findings.map(f =>
            `"${f.question.replace(/"/g, '""')}","${f.answer.replace(/"/g, '""')}","${f.status}","${f.severity}","${f.category}","${f.citations.map(c => c.quote).join('; ').replace(/"/g, '""')}"`
        ).join("\n");

        const blob = new Blob([csvHeader + csvRows], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `audit_${result.audit_id}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
                        <Shield className="w-6 h-6 text-blue-600" />
                        Auto-Audit
                    </h1>
                    <p className="text-sm text-gray-500 mt-1">
                        Run automated risk checks against your Data Room.
                    </p>
                </div>

                {result && (
                    <Button variant="outline" onClick={handleExport} className="gap-2">
                        <FileDown className="w-4 h-4" />
                        Export CSV
                    </Button>
                )}
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-4 p-4 bg-white border rounded-lg shadow-sm">
                <div className="flex-1 min-w-[200px]">
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1 block">
                        Audit Template
                    </label>
                    <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                        <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select a template..." />
                        </SelectTrigger>
                        <SelectContent>
                            {templates.map((t) => (
                                <SelectItem key={t.id} value={t.id}>
                                    {t.name} ({t.question_count} checks)
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                <div>
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1 block">
                        Target Folder
                    </label>
                    <FolderFilter
                        docs={docs}
                        selectedFolder={selectedFolder}
                        onSelect={setSelectedFolder}
                    />
                </div>

                <div className="flex-shrink-0 pt-5">
                    <Button
                        onClick={handleRunAudit}
                        disabled={isRunning || !selectedTemplate}
                        className="gap-2"
                    >
                        {isRunning ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Play className="w-4 h-4" />
                        )}
                        {isRunning ? "Running..." : "Run Audit"}
                    </Button>
                </div>
            </div>

            {/* Summary Cards */}
            {result && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div className="bg-white border rounded-lg p-4 text-center">
                        <div className="text-3xl font-bold text-green-600">{result.summary.found}</div>
                        <div className="text-xs text-gray-500 uppercase tracking-wide">Found</div>
                    </div>
                    <div className="bg-white border rounded-lg p-4 text-center">
                        <div className="text-3xl font-bold text-gray-400">{result.summary.not_found}</div>
                        <div className="text-xs text-gray-500 uppercase tracking-wide">Not Found</div>
                    </div>
                    <div className="bg-white border rounded-lg p-4 text-center">
                        <div className="text-3xl font-bold text-yellow-500">{result.summary.unclear}</div>
                        <div className="text-xs text-gray-500 uppercase tracking-wide">Unclear</div>
                    </div>
                    <div className="bg-white border rounded-lg p-4 text-center">
                        <div className="text-3xl font-bold text-red-500">{result.summary.errors}</div>
                        <div className="text-xs text-gray-500 uppercase tracking-wide">Errors</div>
                    </div>
                    <div className="bg-white border rounded-lg p-4 text-center border-red-200 bg-red-50">
                        <div className="text-3xl font-bold text-red-600">{result.summary.high_risk}</div>
                        <div className="text-xs text-red-600 uppercase tracking-wide font-semibold">High Risk</div>
                    </div>
                </div>
            )}

            {/* Findings Table */}
            {result && (
                <div className="bg-white border rounded-lg overflow-hidden">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[40%]">Question</TableHead>
                                <TableHead className="w-[30%]">Finding</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Severity</TableHead>
                                <TableHead>Category</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {result.findings.map((finding, idx) => {
                                const StatusIcon = statusConfig[finding.status]?.icon || HelpCircle;
                                const SeverityIcon = severityConfig[finding.severity]?.icon || Shield;

                                return (
                                    <TableRow key={idx}>
                                        <TableCell className="font-medium text-sm">
                                            {finding.question}
                                        </TableCell>
                                        <TableCell className="text-sm text-gray-600">
                                            <div className="line-clamp-3">
                                                {finding.answer}
                                            </div>
                                            {finding.citations.length > 0 && (
                                                <div className="mt-1 text-xs text-blue-500">
                                                    {finding.citations.length} citation(s)
                                                </div>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${statusConfig[finding.status]?.color}`}>
                                                <StatusIcon className="w-3 h-3" />
                                                {statusConfig[finding.status]?.label}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${severityConfig[finding.severity]?.color}`}>
                                                <SeverityIcon className="w-3 h-3" />
                                                {finding.severity}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-sm text-gray-500">
                                            {finding.category}
                                        </TableCell>
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>
                </div>
            )}

            {/* Empty State */}
            {!result && !isRunning && (
                <div className="text-center py-20 text-gray-400">
                    <Shield className="w-16 h-16 mx-auto mb-4 opacity-30" />
                    <p className="text-lg">Select a template and run an audit to see findings.</p>
                </div>
            )}

            {/* Loading State */}
            {isRunning && (
                <div className="text-center py-20">
                    <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin text-blue-500" />
                    <p className="text-lg text-gray-600">Running audit checks...</p>
                    <p className="text-sm text-gray-400 mt-1">This may take a few minutes for large Data Rooms.</p>
                </div>
            )}
        </div>
    );
}
