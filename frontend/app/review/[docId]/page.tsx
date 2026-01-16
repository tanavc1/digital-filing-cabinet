"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getDocument, getDocumentContent, updateClause, createIssue } from "@/lib/api";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
    ArrowLeft,
    Check,
    Edit2,
    Flag,
    HelpCircle,
    Loader2,
    Save,
    X,
    AlertTriangle,
    CheckCircle,
    Minus
} from "lucide-react";

interface Evidence {
    file: string;
    page: number;
    snippet: string;
    char_start: number;
    char_end: number;
}

interface ClauseData {
    id: string;
    clause_type: string;
    extracted_value: string;
    status: "resolved" | "needs_review" | "unresolved" | "not_applicable";
    evidence: Evidence[];
    explanation: string;
    snippet: string;
    page_number: number;
    confidence: number;
    verified: boolean;
    flagged: boolean;
}

const CLAUSE_LABELS: Record<string, string> = {
    assignment_consent: "Assignment/Consent",
    change_of_control: "Change of Control",
    term_renewal: "Term/Renewal",
    termination_notice: "Termination/Notice",
    liability_cap: "Liability Cap",
    governing_law: "Governing Law",
    mfn_exclusivity: "MFN/Exclusivity",
    severance: "Severance",
    non_compete: "Non-Compete",
    ip_license: "IP License Type",
};

export default function DocumentReviewPage() {
    const { docId } = useParams<{ docId: string }>();
    const router = useRouter();
    const { workspace } = useWorkspace();
    const workspaceId = workspace?.id || "Main";

    const [document, setDocument] = useState<any>(null);
    const [content, setContent] = useState<string>("");
    const [clauses, setClauses] = useState<ClauseData[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [showUnresolvedOnly, setShowUnresolvedOnly] = useState(false);
    const [editingClause, setEditingClause] = useState<string | null>(null);
    const [editValue, setEditValue] = useState("");
    const [highlightRange, setHighlightRange] = useState<{ start: number; end: number } | null>(null);

    useEffect(() => {
        if (docId) {
            loadDocument();
        }
    }, [docId]);

    async function loadDocument() {
        try {
            setLoading(true);

            // Load document metadata
            const docData = await getDocument(docId as string, workspaceId);
            setDocument(docData);

            // Load document content
            const contentData = await getDocumentContent(docId as string, workspaceId);
            setContent(contentData.content || "");

            // Load clauses for this doc from matrix
            const matrixRes = await fetch(`http://localhost:8000/clauses/matrix?workspace_id=${workspaceId}`);
            const matrix = await matrixRes.json();

            // Find this doc's row and extract clauses
            const docRow = matrix.rows?.find((r: any) => r.doc_id === docId);
            if (docRow?.clauses) {
                const clauseList = Object.entries(docRow.clauses).map(([type, data]: [string, any]) => ({
                    ...data,
                    clause_type: type,
                }));
                setClauses(clauseList);
            }
        } catch (err) {
            console.error("Failed to load document:", err);
        } finally {
            setLoading(false);
        }
    }

    // Filter clauses based on toggle
    const visibleClauses = useMemo(() => {
        if (!showUnresolvedOnly) return clauses;
        return clauses.filter(c => c.status === "unresolved" || c.status === "needs_review");
    }, [clauses, showUnresolvedOnly]);

    // Count stats
    const reviewedCount = clauses.filter(c => c.verified).length;
    const totalCount = clauses.length;
    const unresolvedCount = clauses.filter(c => c.status === "unresolved" || c.status === "needs_review").length;

    function getStatusIcon(status: string) {
        switch (status) {
            case "resolved": return <CheckCircle className="h-4 w-4 text-green-500" />;
            case "needs_review": return <AlertTriangle className="h-4 w-4 text-amber-500" />;
            case "unresolved": return <HelpCircle className="h-4 w-4 text-slate-400" />;
            case "not_applicable": return <Minus className="h-4 w-4 text-gray-400" />;
            default: return null;
        }
    }

    function getStatusBadge(status: string) {
        switch (status) {
            case "resolved": return <Badge className="bg-green-100 text-green-800">Resolved</Badge>;
            case "needs_review": return <Badge className="bg-amber-100 text-amber-800">Needs Review</Badge>;
            case "unresolved": return <Badge className="bg-slate-100 text-slate-600">Unresolved</Badge>;
            case "not_applicable": return <Badge variant="outline">N/A</Badge>;
            default: return null;
        }
    }

    async function handleAccept(clause: ClauseData) {
        try {
            setSaving(true);
            await updateClause(clause.id, { verified: true });
            setClauses(prev => prev.map(c => c.id === clause.id ? { ...c, verified: true } : c));
        } catch (err) {
            console.error("Failed to accept clause:", err);
        } finally {
            setSaving(false);
        }
    }

    async function handleSaveEdit(clause: ClauseData) {
        try {
            setSaving(true);
            // TODO: Update clause value via API
            setClauses(prev => prev.map(c =>
                c.id === clause.id ? { ...c, extracted_value: editValue, verified: true } : c
            ));
            setEditingClause(null);
            setEditValue("");
        } catch (err) {
            console.error("Failed to save edit:", err);
        } finally {
            setSaving(false);
        }
    }

    async function handleFlag(clause: ClauseData) {
        try {
            setSaving(true);
            await updateClause(clause.id, { flagged: true });
            // Create issue auto-linked to this clause
            await createIssue({
                title: `${CLAUSE_LABELS[clause.clause_type] || clause.clause_type} requires attention`,
                description: `Flagged during review. Evidence: ${clause.evidence[0]?.snippet || clause.explanation}`,
                severity: "warning",
                doc_id: docId as string,
                clause_id: clause.id,
            });
            setClauses(prev => prev.map(c => c.id === clause.id ? { ...c, flagged: true } : c));
        } catch (err) {
            console.error("Failed to flag clause:", err);
        } finally {
            setSaving(false);
        }
    }

    function handleHighlightEvidence(clause: ClauseData) {
        if (clause.evidence.length > 0) {
            const ev = clause.evidence[0];
            setHighlightRange({ start: ev.char_start, end: ev.char_end });
        }
    }

    // Render content with highlight
    const renderedContent = useMemo(() => {
        if (!highlightRange || !content) return content;

        const before = content.slice(0, highlightRange.start);
        const highlighted = content.slice(highlightRange.start, highlightRange.end);
        const after = content.slice(highlightRange.end);

        return (
            <>
                {before}
                <mark className="bg-yellow-200 px-0.5">{highlighted}</mark>
                {after}
            </>
        );
    }, [content, highlightRange]);

    if (loading) {
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
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="sm" asChild>
                        <Link href="/review-queue">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back
                        </Link>
                    </Button>
                    <h1 className="font-semibold text-lg truncate max-w-[300px]">
                        {document?.title || "Document Review"}
                    </h1>
                    <Badge variant="outline">{document?.doc_type || "Unknown"}</Badge>
                </div>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-muted-foreground">
                        Progress: {reviewedCount}/{totalCount} reviewed
                    </span>
                    <Button disabled={saving}>
                        <Save className="h-4 w-4 mr-2" />
                        {saving ? "Saving..." : "Save & Continue"}
                    </Button>
                </div>
            </header>

            {/* Split View */}
            <div className="flex flex-1 overflow-hidden">
                {/* Left: Document Viewer */}
                <div className="w-1/2 border-r bg-white overflow-auto">
                    <div className="p-6">
                        <pre className="font-mono text-sm whitespace-pre-wrap break-words leading-relaxed">
                            {renderedContent}
                        </pre>
                    </div>
                </div>

                {/* Right: Playbook Fields */}
                <div className="w-1/2 overflow-auto bg-slate-50/50">
                    <div className="p-4 border-b bg-white sticky top-0 z-10">
                        <div className="flex items-center justify-between">
                            <h2 className="font-semibold">Playbook Fields</h2>
                            <div className="flex items-center gap-2">
                                <Switch
                                    id="unresolved-only"
                                    checked={showUnresolvedOnly}
                                    onCheckedChange={setShowUnresolvedOnly}
                                />
                                <Label htmlFor="unresolved-only" className="text-sm">
                                    Unresolved only ({unresolvedCount})
                                </Label>
                            </div>
                        </div>
                    </div>

                    <div className="p-4 space-y-4">
                        {visibleClauses.length === 0 ? (
                            <div className="text-center py-8 text-muted-foreground">
                                {showUnresolvedOnly
                                    ? "All clauses are resolved! 🎉"
                                    : "No clause extractions for this document."
                                }
                            </div>
                        ) : (
                            visibleClauses.map(clause => (
                                <Card
                                    key={clause.id}
                                    className={`cursor-pointer transition-all ${clause.verified ? "opacity-60" : ""
                                        } ${clause.flagged ? "border-red-300 bg-red-50" : ""
                                        }`}
                                    onClick={() => handleHighlightEvidence(clause)}
                                >
                                    <CardHeader className="pb-2">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                {getStatusIcon(clause.status)}
                                                <CardTitle className="text-sm font-medium">
                                                    {CLAUSE_LABELS[clause.clause_type] || clause.clause_type}
                                                </CardTitle>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {getStatusBadge(clause.status)}
                                                {clause.status !== "not_applicable" && (
                                                    <span className="text-xs text-muted-foreground">
                                                        {Math.round(clause.confidence * 100)}%
                                                    </span>
                                                )}
                                                {clause.verified && (
                                                    <Check className="h-4 w-4 text-green-500" />
                                                )}
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="space-y-3">
                                        {/* Value */}
                                        {editingClause === clause.id ? (
                                            <div className="space-y-2">
                                                <Input
                                                    value={editValue}
                                                    onChange={(e) => setEditValue(e.target.value)}
                                                    placeholder="Enter value..."
                                                />
                                                <div className="flex gap-2">
                                                    <Button
                                                        size="sm"
                                                        onClick={() => handleSaveEdit(clause)}
                                                    >
                                                        Save
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => setEditingClause(null)}
                                                    >
                                                        Cancel
                                                    </Button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="text-sm">
                                                {clause.status === "resolved" || clause.status === "needs_review" ? (
                                                    <span className="font-medium">{clause.extracted_value}</span>
                                                ) : (
                                                    <span className="text-muted-foreground italic">
                                                        {clause.explanation || "No value extracted"}
                                                    </span>
                                                )}
                                            </div>
                                        )}

                                        {/* Evidence snippet */}
                                        {clause.evidence.length > 0 && (
                                            <div className="text-xs bg-slate-100 p-2 rounded border-l-2 border-indigo-400">
                                                <span className="font-medium">p.{clause.evidence[0].page}:</span>{" "}
                                                "{clause.evidence[0].snippet.slice(0, 100)}..."
                                            </div>
                                        )}

                                        {/* Actions */}
                                        {!clause.verified && clause.status !== "not_applicable" && (
                                            <div className="flex gap-2 pt-2">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={(e) => { e.stopPropagation(); handleAccept(clause); }}
                                                    disabled={saving}
                                                >
                                                    <Check className="h-3 w-3 mr-1" />
                                                    Accept
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setEditingClause(clause.id);
                                                        setEditValue(clause.extracted_value);
                                                    }}
                                                >
                                                    <Edit2 className="h-3 w-3 mr-1" />
                                                    Edit
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    className="text-red-600 hover:text-red-700"
                                                    onClick={(e) => { e.stopPropagation(); handleFlag(clause); }}
                                                    disabled={saving || clause.flagged}
                                                >
                                                    <Flag className="h-3 w-3 mr-1" />
                                                    Flag Issue
                                                </Button>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
