"use client";

import { useEffect, useState } from "react";
import { getReviews, updateReview, bulkAssignReviews, bulkUpdateStatus, Review } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
    AlertCircle,
    CheckCircle,
    Clock,
    Loader2,
    Users,
    Filter,
    FileText,
    ShieldCheck,
    Search
} from "lucide-react";
import Link from "next/link";
import { useWorkspace } from "@/components/providers/workspace-provider";

export default function ReviewQueuePage() {
    const { workspace } = useWorkspace();
    const [reviews, setReviews] = useState<Review[]>([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [assignee, setAssignee] = useState("");

    // Filters
    const [statusFilter, setStatusFilter] = useState("all");
    const [riskFilter, setRiskFilter] = useState("all");
    const [search, setSearch] = useState("");

    useEffect(() => {
        loadReviews();
    }, [workspace.id]);

    async function loadReviews() {
        try {
            setLoading(true);
            const data = await getReviews(workspace.id);
            setReviews(data.reviews || []);
        } catch (err) {
            console.error("Failed to load reviews:", err);
        } finally {
            setLoading(false);
        }
    }

    // --- Selection Logic ---
    function toggleSelect(docId: string) {
        const newSelected = new Set(selected);
        if (newSelected.has(docId)) newSelected.delete(docId);
        else newSelected.add(docId);
        setSelected(newSelected);
    }

    function selectAll(currentViewDocs: Review[]) {
        if (selected.size === currentViewDocs.length) {
            setSelected(new Set());
        } else {
            setSelected(new Set(currentViewDocs.map(r => r.doc_id)));
        }
    }

    // --- Bulk Actions ---
    async function handleBulkAssign() {
        if (!assignee.trim() || selected.size === 0) return;
        await bulkAssignReviews(Array.from(selected), assignee);
        setSelected(new Set());
        loadReviews();
    }

    async function handleBulkStatus(status: string) {
        if (selected.size === 0) return;
        await bulkUpdateStatus(Array.from(selected), status);
        setSelected(new Set());
        loadReviews();
    }

    async function handleStatusChange(docId: string, status: string) {
        await updateReview(docId, { status });
        loadReviews();
    }

    // --- Render Helpers ---
    function getRiskBadge(level: string) {
        switch (level) {
            case "High": return <Badge variant="destructive" className="w-20 justify-center">High</Badge>;
            case "Medium": return <Badge className="bg-amber-500 w-20 justify-center">Medium</Badge>;
            case "Low": return <Badge className="bg-green-500 w-20 justify-center">Low</Badge>;
            default: return <Badge variant="secondary" className="w-20 justify-center">{level}</Badge>;
        }
    }

    function getStatusIcon(status: string) {
        switch (status) {
            case "qa_approved": return <ShieldCheck className="h-4 w-4 text-emerald-600" />;
            case "qa_needed": return <ShieldCheck className="h-4 w-4 text-purple-500" />;
            case "reviewed": return <CheckCircle className="h-4 w-4 text-green-500" />;
            case "in_review": return <Clock className="h-4 w-4 text-amber-500" />;
            case "flagged": return <AlertCircle className="h-4 w-4 text-red-500" />;
            default: return <FileText className="h-4 w-4 text-gray-400" />;
        }
    }

    // --- Filter Logic ---
    const filterReviews = (docs: Review[]) => {
        return docs.filter(r => {
            if (statusFilter !== "all" && r.status !== statusFilter) return false;
            if (riskFilter !== "all" && r.risk_level !== riskFilter) return false;
            if (search && !r.doc_title.toLowerCase().includes(search.toLowerCase())) return false;
            return true;
        });
    };

    const allFiltered = filterReviews(reviews);

    // Derived queues
    // For demo, "My" = Assigned to 'Me' or 'DemoUser' or empty assignment if we assume unassigned is grab-bag
    const myQueue = allFiltered.filter(r => r.assigned_to === "Me" || r.status === "in_review");
    const qaQueue = allFiltered.filter(r => r.status === "qa_needed" || r.status === "flagged");

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-screen bg-slate-50">
            {/* Header */}
            <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-bold flex items-center gap-2">
                        <FileText className="text-indigo-600" />
                        Review Queue
                    </h1>
                    <p className="text-sm text-gray-500">Manage assignments and track progress</p>
                </div>
                <div className="flex gap-2">
                    {/* Bulk Actions Bar */}
                    {selected.size > 0 && (
                        <div className="flex items-center gap-2 bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-100 animate-in fade-in slide-in-from-top-2">
                            <div className="text-xs font-semibold text-indigo-700 bg-white px-2 py-0.5 rounded shadow-sm border">
                                {selected.size} Selected
                            </div>
                            <div className="h-4 w-[1px] bg-indigo-200 mx-1"></div>
                            <Input
                                placeholder="Assign..."
                                className="h-7 w-28 text-xs"
                                value={assignee}
                                onChange={e => setAssignee(e.target.value)}
                            />
                            <Button size="sm" variant="ghost" className="h-7 px-2 text-indigo-700" onClick={handleBulkAssign}>
                                Assign
                            </Button>
                            <div className="h-4 w-[1px] bg-indigo-200 mx-1"></div>
                            <Button size="sm" variant="ghost" className="h-7 px-2 text-indigo-700" onClick={() => handleBulkStatus("reviewed")}>
                                Mark Reviewed
                            </Button>
                        </div>
                    )}
                </div>
            </div>

            <div className="flex-1 p-6 overflow-hidden flex flex-col">
                <Tabs defaultValue="all" className="flex-1 flex flex-col">
                    <div className="flex justify-between items-center mb-4">
                        <TabsList>
                            <TabsTrigger value="all">All Docs ({allFiltered.length})</TabsTrigger>
                            <TabsTrigger value="my">My Queue ({myQueue.length})</TabsTrigger>
                            <TabsTrigger value="qa">QA Queue ({qaQueue.length})</TabsTrigger>
                        </TabsList>

                        <div className="flex gap-2">
                            <div className="relative">
                                <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
                                <Input
                                    placeholder="Search docs..."
                                    className="pl-8 w-64"
                                    value={search}
                                    onChange={e => setSearch(e.target.value)}
                                />
                            </div>
                            <Select value={riskFilter} onValueChange={setRiskFilter}>
                                <SelectTrigger className="w-32">
                                    <SelectValue placeholder="Risk" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Risk</SelectItem>
                                    <SelectItem value="High">High Risk</SelectItem>
                                    <SelectItem value="Medium">Medium</SelectItem>
                                    <SelectItem value="Low">Low</SelectItem>
                                </SelectContent>
                            </Select>
                            <Select value={statusFilter} onValueChange={setStatusFilter}>
                                <SelectTrigger className="w-32">
                                    <SelectValue placeholder="Status" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Status</SelectItem>
                                    <SelectItem value="unreviewed">Unreviewed</SelectItem>
                                    <SelectItem value="in_review">In Review</SelectItem>
                                    <SelectItem value="reviewed">Reviewed</SelectItem>
                                    <SelectItem value="qa_needed">QA Needed</SelectItem>
                                    <SelectItem value="qa_approved">QA Approved</SelectItem>
                                    <SelectItem value="flagged">Flagged</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {["all", "my", "qa"].map(tab => {
                        const currentDocs = tab === "all" ? allFiltered : tab === "my" ? myQueue : qaQueue;
                        return (
                            <TabsContent key={tab} value={tab} className="flex-1 overflow-auto border rounded-md bg-white shadow-sm mt-0">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead className="w-10">
                                                <Checkbox
                                                    checked={selected.size === currentDocs.length && currentDocs.length > 0}
                                                    onCheckedChange={() => selectAll(currentDocs)}
                                                />
                                            </TableHead>
                                            <TableHead>Document</TableHead>
                                            <TableHead>Folder</TableHead>
                                            <TableHead className="text-center">Risk</TableHead>
                                            <TableHead className="text-center">Status</TableHead>
                                            <TableHead>Assigned To</TableHead>
                                            <TableHead className="text-center">Conf.</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {currentDocs.map(r => (
                                            <TableRow key={r.doc_id}>
                                                <TableCell>
                                                    <Checkbox
                                                        checked={selected.has(r.doc_id)}
                                                        onCheckedChange={() => toggleSelect(r.doc_id)}
                                                    />
                                                </TableCell>
                                                <TableCell className="font-medium">
                                                    <Link href={`/viewer/${r.doc_id}?workspace_id=${workspace.id}`} className="text-indigo-600 hover:underline">
                                                        {r.doc_title}
                                                    </Link>
                                                </TableCell>
                                                <TableCell className="text-muted-foreground text-sm">{r.folder_path}</TableCell>
                                                <TableCell className="text-center">{getRiskBadge(r.risk_level)}</TableCell>
                                                <TableCell>
                                                    <Select value={r.status} onValueChange={(val) => handleStatusChange(r.doc_id, val)}>
                                                        <SelectTrigger className="h-8 w-36 mx-auto">
                                                            <div className="flex items-center gap-2 text-xs">
                                                                {getStatusIcon(r.status)}
                                                                <SelectValue />
                                                            </div>
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="unreviewed">Unreviewed</SelectItem>
                                                            <SelectItem value="in_review">In Review</SelectItem>
                                                            <SelectItem value="reviewed">Reviewed</SelectItem>
                                                            <SelectItem value="qa_needed">QA Needed</SelectItem>
                                                            <SelectItem value="qa_approved">QA Approved</SelectItem>
                                                            <SelectItem value="flagged">Flagged</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </TableCell>
                                                <TableCell className="text-sm">{r.assigned_to || "-"}</TableCell>
                                                <TableCell className="text-center">
                                                    <Badge variant="outline" className={r.confidence > 0.8 ? "text-green-600 border-green-200" : "text-amber-600 border-amber-200"}>
                                                        {Math.round(r.confidence * 100)}%
                                                    </Badge>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                        {currentDocs.length === 0 && (
                                            <TableRow>
                                                <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                                                    No documents in this queue.
                                                </TableCell>
                                            </TableRow>
                                        )}
                                    </TableBody>
                                </Table>
                            </TabsContent>
                        );
                    })}
                </Tabs>
            </div>
        </div>
    );
}
