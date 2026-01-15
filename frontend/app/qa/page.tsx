"use client";

import { useEffect, useState } from "react";
import { getReviews, updateReview, bulkUpdateStatus, Review } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    CheckCircle,
    Loader2,
    ShieldCheck,
    FileText,
    AlertTriangle,
    Flag
} from "lucide-react";
import Link from "next/link";
import { useWorkspace } from "@/components/providers/workspace-provider";

export default function QAPage() {
    const { workspace } = useWorkspace();
    const [reviews, setReviews] = useState<Review[]>([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState<Set<string>>(new Set());

    useEffect(() => {
        loadReviews();
    }, [workspace.id]);

    async function loadReviews() {
        try {
            setLoading(true);
            const data = await getReviews(workspace.id, { status: "qa_needed" });
            // Also fetch flagged? For now just qa_needed
            setReviews(data.reviews || []);
        } catch (err) {
            console.error("Failed to load QA reviews:", err);
        } finally {
            setLoading(false);
        }
    }

    function toggleSelect(docId: string) {
        const newSelected = new Set(selected);
        if (newSelected.has(docId)) newSelected.delete(docId);
        else newSelected.add(docId);
        setSelected(newSelected);
    }

    function selectAll() {
        if (selected.size === reviews.length) {
            setSelected(new Set());
        } else {
            setSelected(new Set(reviews.map(r => r.doc_id)));
        }
    }

    async function handleBulkApprove() {
        if (selected.size === 0) return;
        await bulkUpdateStatus(Array.from(selected), "qa_approved");
        setSelected(new Set());
        loadReviews();
    }

    async function handleApprove(docId: string) {
        await updateReview(docId, { status: "qa_approved" });
        loadReviews();
    }

    async function handleReject(docId: string) {
        await updateReview(docId, { status: "flagged" }); // Send back to flagged/unreviewed? "flagged" implies issue.
        loadReviews();
    }

    if (loading) return <div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin h-8 w-8 text-indigo-600" /></div>;

    return (
        <div className="flex flex-col h-screen bg-slate-50">
            <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-bold flex items-center gap-2 text-indigo-900">
                        <ShieldCheck className="text-indigo-600" />
                        Quality Assurance
                    </h1>
                    <p className="text-sm text-gray-500">Verify diligence accuracy before delivery</p>
                </div>
                <div className="flex gap-2">
                    {selected.size > 0 && (
                        <div className="flex items-center gap-2 bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-100 animate-in fade-in">
                            <span className="text-xs font-semibold text-indigo-700">{selected.size} Selected</span>
                            <Button size="sm" className="h-7 bg-green-600 hover:bg-green-700" onClick={handleBulkApprove}>
                                <CheckCircle className="w-3 h-3 mr-1" /> Approve All
                            </Button>
                        </div>
                    )}
                </div>
            </div>

            <div className="p-6 overflow-auto">
                <Card className="border-t-4 border-t-indigo-500 shadow-sm">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-10"><Checkbox checked={selected.size === reviews.length && reviews.length > 0} onCheckedChange={selectAll} /></TableHead>
                                <TableHead>Document</TableHead>
                                <TableHead>Reviewer</TableHead>
                                <TableHead className="text-center">Confidence</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {reviews.map(r => (
                                <TableRow key={r.doc_id}>
                                    <TableCell><Checkbox checked={selected.has(r.doc_id)} onCheckedChange={() => toggleSelect(r.doc_id)} /></TableCell>
                                    <TableCell>
                                        <div className="flex flex-col">
                                            <Link href={`/viewer/${r.doc_id}?workspace_id=${workspace.id}`} className="font-medium text-indigo-600 hover:underline">
                                                {r.doc_title}
                                            </Link>
                                            <span className="text-xs text-gray-500">{r.doc_type}</span>
                                        </div>
                                    </TableCell>
                                    <TableCell>{r.assigned_to || "Unassigned"}</TableCell>
                                    <TableCell className="text-center">
                                        <Badge variant="outline" className={r.confidence > 0.8 ? "text-green-600 border-green-200" : "text-amber-600 border-amber-200"}>
                                            {Math.round(r.confidence * 100)}%
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <div className="flex justify-end gap-2">
                                            <Button size="sm" variant="ghost" className="text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => handleReject(r.doc_id)}>
                                                <Flag className="w-4 h-4" />
                                            </Button>
                                            <Button size="sm" variant="ghost" className="text-green-600 hover:text-green-700 hover:bg-green-50" onClick={() => handleApprove(r.doc_id)}>
                                                <CheckCircle className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ))}
                            {reviews.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={5} className="h-32 text-center text-gray-500">
                                        <div className="flex flex-col items-center gap-2">
                                            <CheckCircle className="w-8 h-8 text-green-100" />
                                            <p>Unless you're slacking, great job! No documents pending QA.</p>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </Card>
            </div>
        </div>
    );
}
