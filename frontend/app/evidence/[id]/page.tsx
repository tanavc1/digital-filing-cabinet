"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getClause, updateClause, createIssue, ClauseExtraction } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
    CheckCircle,
    Flag,
    AlertTriangle,
    Loader2,
    ArrowLeft,
    FileText,
    Quote
} from "lucide-react";
import Link from "next/link";

export default function EvidencePage() {
    const params = useParams();
    const clauseId = params.id as string;

    const [clause, setClause] = useState<ClauseExtraction | null>(null);
    const [loading, setLoading] = useState(true);
    const [issueNote, setIssueNote] = useState("");
    const [creatingIssue, setCreatingIssue] = useState(false);

    useEffect(() => {
        loadClause();
    }, [clauseId]);

    async function loadClause() {
        try {
            setLoading(true);
            const data = await getClause(clauseId);
            setClause(data);
        } catch (err) {
            console.error("Failed to load clause:", err);
        } finally {
            setLoading(false);
        }
    }

    async function handleVerify() {
        if (!clause) return;
        await updateClause(clauseId, { verified: !clause.verified });
        loadClause();
    }

    async function handleFlag() {
        if (!clause) return;
        await updateClause(clauseId, { flagged: !clause.flagged });
        loadClause();
    }

    async function handleCreateIssue() {
        if (!clause) return;

        try {
            setCreatingIssue(true);
            await createIssue({
                title: `${clause.clause_type} - ${clause.doc_title}`,
                description: issueNote || clause.snippet,
                severity: "warning",
                doc_id: clause.doc_id,
                doc_title: clause.doc_title,
                clause_id: clause.id,
                action_required: "Review and assess",
            });
            setIssueNote("");
            alert("Issue created successfully!");
        } catch (err) {
            console.error("Failed to create issue:", err);
        } finally {
            setCreatingIssue(false);
        }
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

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    if (!clause) {
        return (
            <div className="flex h-screen flex-col items-center justify-center">
                <AlertTriangle className="h-12 w-12 text-amber-500 mb-4" />
                <p>Clause not found</p>
                <Button asChild className="mt-4">
                    <Link href="/clause-matrix">Back to Matrix</Link>
                </Button>
            </div>
        );
    }

    return (
        <div className="flex h-screen flex-col bg-slate-50/50">
            {/* Header */}
            <header className="flex h-14 items-center gap-4 border-b bg-white px-6 shadow-sm">
                <Button variant="ghost" size="icon" asChild>
                    <Link href="/clause-matrix">
                        <ArrowLeft className="h-4 w-4" />
                    </Link>
                </Button>
                <div className="flex items-center gap-2">
                    <Quote className="h-5 w-5 text-indigo-600" />
                    <h1 className="font-semibold text-lg">Evidence Viewer</h1>
                </div>
                <div className="flex items-center gap-2 ml-auto">
                    {clause.verified && (
                        <Badge className="bg-green-100 text-green-800">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Verified
                        </Badge>
                    )}
                    {clause.flagged && (
                        <Badge variant="destructive">
                            <Flag className="h-3 w-3 mr-1" />
                            Flagged
                        </Badge>
                    )}
                </div>
            </header>

            <main className="flex-1 overflow-auto p-6">
                <div className="max-w-4xl mx-auto space-y-6">
                    {/* Document Info */}
                    <Card>
                        <CardHeader>
                            <div className="flex items-start justify-between">
                                <div>
                                    <CardTitle className="flex items-center gap-2">
                                        <FileText className="h-5 w-5 text-indigo-600" />
                                        {clause.doc_title}
                                    </CardTitle>
                                    <CardDescription>
                                        {CLAUSE_LABELS[clause.clause_type] || clause.clause_type}
                                        {clause.page_number > 0 && ` • Page ${clause.page_number}`}
                                    </CardDescription>
                                </div>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <span>Confidence:</span>
                                    <div className="w-20 bg-gray-200 rounded-full h-2">
                                        <div
                                            className="bg-indigo-600 h-2 rounded-full"
                                            style={{ width: `${clause.confidence * 100}%` }}
                                        />
                                    </div>
                                    <span>{Math.round(clause.confidence * 100)}%</span>
                                </div>
                            </div>
                        </CardHeader>
                    </Card>

                    {/* Extracted Value */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Extracted Value</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-100">
                                <p className="text-lg font-medium text-indigo-900 break-words">
                                    {clause.extracted_value || "No value extracted"}
                                </p>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Snippet / Quote */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base flex items-center gap-2">
                                <Quote className="h-4 w-4" />
                                Source Text
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <blockquote className="border-l-4 border-gray-300 pl-4 italic text-gray-700 bg-gray-50 p-4 rounded-r-lg break-words">
                                "{clause.snippet}"
                            </blockquote>
                        </CardContent>
                    </Card>

                    {/* Actions */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Actions</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex gap-3">
                                <Button
                                    variant={clause.verified ? "default" : "outline"}
                                    onClick={handleVerify}
                                    className={clause.verified ? "bg-green-600 hover:bg-green-700" : ""}
                                >
                                    <CheckCircle className="h-4 w-4 mr-2" />
                                    {clause.verified ? "Verified" : "Confirm"}
                                </Button>
                                <Button
                                    variant={clause.flagged ? "destructive" : "outline"}
                                    onClick={handleFlag}
                                >
                                    <Flag className="h-4 w-4 mr-2" />
                                    {clause.flagged ? "Unflag" : "Flag Issue"}
                                </Button>
                            </div>

                            <div className="border-t pt-4">
                                <label className="text-sm font-medium mb-2 block">Create Issue</label>
                                <Textarea
                                    placeholder="Add notes about this issue..."
                                    value={issueNote}
                                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setIssueNote(e.target.value)}
                                    className="mb-2"
                                />
                                <Button
                                    onClick={handleCreateIssue}
                                    disabled={creatingIssue}
                                    variant="secondary"
                                >
                                    {creatingIssue ? (
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    ) : (
                                        <AlertTriangle className="h-4 w-4 mr-2" />
                                    )}
                                    Create Issue
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </main>
        </div>
    );
}
