"use client";

import { useState, useMemo } from "react";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { compareDocuments, CompareResult, DifferenceItem } from "@/lib/api";
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
    GitCompare,
    ArrowRight,
    AlertTriangle,
    ChevronDown,
    ChevronUp,
    Loader2,
    FileText,
    Minus,
    Plus
} from "lucide-react";
import { toast } from "sonner";

// Severity styling
const severityConfig = {
    HIGH: { color: "bg-red-100 text-red-700 border-red-200", label: "High" },
    MEDIUM: { color: "bg-yellow-100 text-yellow-700 border-yellow-200", label: "Medium" },
    LOW: { color: "bg-blue-100 text-blue-700 border-blue-200", label: "Low" },
};

export default function ComparePage() {
    const { workspace, docs } = useWorkspace();

    // State
    const [docA, setDocA] = useState<string>("");
    const [docB, setDocB] = useState<string>("");
    const [isComparing, setIsComparing] = useState(false);
    const [result, setResult] = useState<CompareResult | null>(null);
    const [expandedRow, setExpandedRow] = useState<number | null>(null);

    // Filter docs for selectors (exclude currently selected)
    const docsForA = useMemo(() => docs.filter(d => d.doc_id !== docB), [docs, docB]);
    const docsForB = useMemo(() => docs.filter(d => d.doc_id !== docA), [docs, docA]);

    // Run comparison
    const handleCompare = async () => {
        if (!docA || !docB) {
            toast.error("Please select two documents to compare");
            return;
        }
        if (docA === docB) {
            toast.error("Please select two different documents");
            return;
        }

        setIsComparing(true);
        setResult(null);
        toast.info("Analyzing documents... This may take a minute.");

        try {
            const compareResult = await compareDocuments(docA, docB, workspace.id);
            setResult(compareResult);

            if (compareResult.error) {
                toast.warning("Comparison completed with warnings");
            } else if (compareResult.differences.length === 0) {
                toast.success("Documents are substantially identical");
            } else {
                toast.success(`Found ${compareResult.stats.total_changes} differences`);
            }
        } catch (err: any) {
            console.error("Comparison failed:", err);
            toast.error(err?.response?.data?.detail || "Comparison failed");
        } finally {
            setIsComparing(false);
        }
    };

    // Get document title by ID
    const getDocTitle = (docId: string) => {
        const doc = docs.find(d => d.doc_id === docId);
        return doc?.title || docId.slice(0, 8);
    };

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
                    <GitCompare className="w-6 h-6 text-purple-600" />
                    Smart Compare
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                    Compare two documents to identify material differences.
                </p>
            </div>

            {/* Document Selectors */}
            <div className="flex flex-wrap items-center gap-4 p-6 bg-white border rounded-lg shadow-sm">
                <div className="flex-1 min-w-[200px]">
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1 block">
                        Original Document
                    </label>
                    <Select value={docA} onValueChange={setDocA}>
                        <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select original..." />
                        </SelectTrigger>
                        <SelectContent>
                            {docsForA.map((doc) => (
                                <SelectItem key={doc.doc_id} value={doc.doc_id}>
                                    <div className="flex items-center gap-2">
                                        <FileText className="w-3 h-3 text-gray-400" />
                                        <span className="truncate max-w-[200px]">{doc.title}</span>
                                    </div>
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                <ArrowRight className="w-5 h-5 text-gray-400 flex-shrink-0 mt-5" />

                <div className="flex-1 min-w-[200px]">
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1 block">
                        Revised Document
                    </label>
                    <Select value={docB} onValueChange={setDocB}>
                        <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select revised..." />
                        </SelectTrigger>
                        <SelectContent>
                            {docsForB.map((doc) => (
                                <SelectItem key={doc.doc_id} value={doc.doc_id}>
                                    <div className="flex items-center gap-2">
                                        <FileText className="w-3 h-3 text-gray-400" />
                                        <span className="truncate max-w-[200px]">{doc.title}</span>
                                    </div>
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                <div className="flex-shrink-0 pt-5">
                    <Button
                        onClick={handleCompare}
                        disabled={isComparing || !docA || !docB}
                        className="gap-2"
                    >
                        {isComparing ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <GitCompare className="w-4 h-4" />
                        )}
                        {isComparing ? "Comparing..." : "Compare"}
                    </Button>
                </div>
            </div>

            {/* Summary */}
            {result && (
                <div className="bg-white border rounded-lg p-6 space-y-4">
                    <div className="flex items-start justify-between">
                        <div>
                            <h2 className="font-semibold text-lg">Comparison Summary</h2>
                            <p className="text-sm text-gray-600 mt-1">{result.summary}</p>
                        </div>
                        <div className="grid grid-cols-4 gap-4 text-center">
                            <div className="px-4 py-2 bg-gray-50 rounded-lg">
                                <div className="text-2xl font-bold">{result.stats.total_changes}</div>
                                <div className="text-xs text-gray-500">Total</div>
                            </div>
                            <div className="px-4 py-2 bg-red-50 rounded-lg">
                                <div className="text-2xl font-bold text-red-600">{result.stats.high_severity}</div>
                                <div className="text-xs text-red-600">High</div>
                            </div>
                            <div className="px-4 py-2 bg-yellow-50 rounded-lg">
                                <div className="text-2xl font-bold text-yellow-600">{result.stats.medium_severity}</div>
                                <div className="text-xs text-yellow-600">Medium</div>
                            </div>
                            <div className="px-4 py-2 bg-blue-50 rounded-lg">
                                <div className="text-2xl font-bold text-blue-600">{result.stats.low_severity}</div>
                                <div className="text-xs text-blue-600">Low</div>
                            </div>
                        </div>
                    </div>

                    {/* Document Info */}
                    <div className="flex items-center gap-4 text-sm text-gray-500 pt-2 border-t">
                        <span><strong>Original:</strong> {result.doc_a.title} ({result.doc_a.chunk_count} chunks)</span>
                        <ArrowRight className="w-4 h-4" />
                        <span><strong>Revised:</strong> {result.doc_b.title} ({result.doc_b.chunk_count} chunks)</span>
                    </div>
                </div>
            )}

            {/* Differences Table */}
            {result && result.differences.length > 0 && (
                <div className="bg-white border rounded-lg overflow-hidden">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[30%]">Change</TableHead>
                                <TableHead>Category</TableHead>
                                <TableHead>Severity</TableHead>
                                <TableHead className="w-12"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {result.differences.map((diff, idx) => (
                                <>
                                    <TableRow
                                        key={idx}
                                        className="cursor-pointer hover:bg-gray-50"
                                        onClick={() => setExpandedRow(expandedRow === idx ? null : idx)}
                                    >
                                        <TableCell className="font-medium">
                                            {diff.description}
                                        </TableCell>
                                        <TableCell className="text-gray-600">
                                            {diff.category}
                                        </TableCell>
                                        <TableCell>
                                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${severityConfig[diff.severity]?.color}`}>
                                                <AlertTriangle className="w-3 h-3" />
                                                {severityConfig[diff.severity]?.label}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            {expandedRow === idx ? (
                                                <ChevronUp className="w-4 h-4 text-gray-400" />
                                            ) : (
                                                <ChevronDown className="w-4 h-4 text-gray-400" />
                                            )}
                                        </TableCell>
                                    </TableRow>

                                    {/* Expanded Detail Row */}
                                    {expandedRow === idx && (
                                        <TableRow className="bg-gray-50">
                                            <TableCell colSpan={4} className="p-4">
                                                <div className="grid grid-cols-2 gap-4">
                                                    {diff.original_text && (
                                                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                                                            <div className="flex items-center gap-1 text-xs font-medium text-red-600 mb-2">
                                                                <Minus className="w-3 h-3" />
                                                                Original
                                                            </div>
                                                            <p className="text-sm text-red-800 line-clamp-4">
                                                                {diff.original_text}
                                                            </p>
                                                        </div>
                                                    )}
                                                    {diff.revised_text && (
                                                        <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                                                            <div className="flex items-center gap-1 text-xs font-medium text-green-600 mb-2">
                                                                <Plus className="w-3 h-3" />
                                                                Revised
                                                            </div>
                                                            <p className="text-sm text-green-800 line-clamp-4">
                                                                {diff.revised_text}
                                                            </p>
                                                        </div>
                                                    )}
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            )}

            {/* No Differences State */}
            {result && result.differences.length === 0 && (
                <div className="text-center py-12 bg-green-50 border border-green-200 rounded-lg">
                    <div className="text-green-600 text-lg font-medium">Documents are substantially identical</div>
                    <p className="text-green-500 mt-1">No material differences were found.</p>
                </div>
            )}

            {/* Empty State */}
            {!result && !isComparing && (
                <div className="text-center py-20 text-gray-400">
                    <GitCompare className="w-16 h-16 mx-auto mb-4 opacity-30" />
                    <p className="text-lg">Select two documents to compare.</p>
                    <p className="text-sm mt-1">We&apos;ll identify material legal and commercial changes.</p>
                </div>
            )}

            {/* Loading State */}
            {isComparing && (
                <div className="text-center py-20">
                    <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin text-purple-500" />
                    <p className="text-lg text-gray-600">Analyzing documents...</p>
                    <p className="text-sm text-gray-400 mt-1">Identifying material differences.</p>
                </div>
            )}
        </div>
    );
}
