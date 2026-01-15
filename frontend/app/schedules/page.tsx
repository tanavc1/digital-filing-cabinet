"use client";

import { useEffect, useState } from "react";
import { FileText, Download, AlertTriangle, CheckCircle, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import api from "@/lib/api";

interface ScheduleType {
    id: string;
    name: string;
}

interface ScheduleItem {
    title: string;
    category: string;
    description: string;
    parties: string[];
    key_terms: string;
    risk_level: string;
    source_doc_id: string;
    source_doc_title: string;
}

interface Schedule {
    schedule_type: string;
    schedule_name: string;
    generated_at: string;
    items: ScheduleItem[];
    summary: string;
    total_count: number;
}

export default function SchedulesPage() {
    const [scheduleTypes, setScheduleTypes] = useState<ScheduleType[]>([]);
    const [selectedType, setSelectedType] = useState<string>("");
    const [schedule, setSchedule] = useState<Schedule | null>(null);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const workspaceId = "default";

    useEffect(() => {
        loadScheduleTypes();
    }, []);

    async function loadScheduleTypes() {
        try {
            setLoading(true);
            setError(null);
            const res = await api.get("/schedules/types");
            setScheduleTypes(res.data.types || []);
            if (res.data.types?.length > 0) {
                setSelectedType(res.data.types[0].id);
            }
        } catch (err) {
            console.error("Failed to load schedule types:", err);
            setError("Unable to connect to backend. Please ensure the server is running.");
        } finally {
            setLoading(false);
        }
    }

    async function generateSchedule() {
        if (!selectedType) return;

        try {
            setGenerating(true);
            setError(null);
            const res = await api.post("/schedules/generate", {
                schedule_type: selectedType,
                workspace_id: workspaceId
            }, { timeout: 180000 }); // 3 min timeout for LLM processing
            setSchedule(res.data);
        } catch (err: any) {
            console.error("Failed to generate schedule:", err);
            setError(err.response?.data?.detail || "Schedule generation failed. Please try again.");
        } finally {
            setGenerating(false);
        }
    }


    function exportToCSV() {
        if (!schedule) return;

        const headers = ["Title", "Category", "Parties", "Key Terms", "Risk Level", "Description"];
        const rows = schedule.items.map(item => [
            item.title,
            item.category,
            item.parties.join("; "),
            item.key_terms,
            item.risk_level,
            item.description.replace(/,/g, ";")
        ]);

        const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${schedule.schedule_name.replace(/\s/g, "_")}.csv`;
        a.click();
    }

    function getRiskBadge(level: string) {
        switch (level) {
            case "High":
                return <Badge variant="destructive">High</Badge>;
            case "Medium":
                return <Badge className="bg-amber-500">Medium</Badge>;
            case "Low":
                return <Badge className="bg-green-500">Low</Badge>;
            default:
                return <Badge variant="secondary">{level}</Badge>;
        }
    }

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="flex h-screen flex-col bg-slate-50/50">
            {/* Header */}
            <header className="flex h-14 items-center justify-between border-b bg-white px-6 shadow-sm">
                <h1 className="font-semibold text-lg">Disclosure Schedules</h1>
                {schedule && (
                    <Button variant="outline" size="sm" onClick={exportToCSV}>
                        <Download className="h-4 w-4 mr-2" />
                        Export CSV
                    </Button>
                )}
            </header>

            <main className="flex-1 overflow-auto p-6 space-y-6">
                {/* Error Alert */}
                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4" />
                        <span className="text-sm">{error}</span>
                    </div>
                )}

                {/* Generator Card */}
                <Card>
                    <CardHeader>
                        <CardTitle>Generate Disclosure Schedule</CardTitle>
                        <CardDescription>
                            Select a schedule type to extract relevant information from all documents in the data room.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex gap-4 items-end">
                            <div className="flex-1">
                                <label className="text-sm font-medium mb-2 block">Schedule Type</label>
                                <Select value={selectedType} onValueChange={setSelectedType}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select schedule type" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {scheduleTypes.map((type) => (
                                            <SelectItem key={type.id} value={type.id}>
                                                {type.name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <Button onClick={generateSchedule} disabled={generating || !selectedType}>
                                {generating ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <FileText className="h-4 w-4 mr-2" />
                                        Generate Schedule
                                    </>
                                )}
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Results */}
                {schedule && (
                    <>
                        {/* Summary Card */}
                        <Card>
                            <CardHeader>
                                <CardTitle>{schedule.schedule_name}</CardTitle>
                                <CardDescription>
                                    Generated at {new Date(schedule.generated_at).toLocaleString()}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-3 gap-4 mb-4">
                                    <div className="text-center p-4 bg-slate-100 rounded-lg">
                                        <div className="text-2xl font-bold">{schedule.total_count}</div>
                                        <div className="text-sm text-muted-foreground">Total Items</div>
                                    </div>
                                    <div className="text-center p-4 bg-red-50 rounded-lg">
                                        <div className="text-2xl font-bold text-red-600">
                                            {schedule.items.filter(i => i.risk_level === "High").length}
                                        </div>
                                        <div className="text-sm text-muted-foreground">High Risk</div>
                                    </div>
                                    <div className="text-center p-4 bg-green-50 rounded-lg">
                                        <div className="text-2xl font-bold text-green-600">
                                            {schedule.items.filter(i => i.risk_level === "Low").length}
                                        </div>
                                        <div className="text-sm text-muted-foreground">Low Risk</div>
                                    </div>
                                </div>
                                <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                                    {schedule.summary}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Items Table */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Schedule Items</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Document</TableHead>
                                            <TableHead>Category</TableHead>
                                            <TableHead>Key Terms</TableHead>
                                            <TableHead>Risk</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {schedule.items.map((item, idx) => (
                                            <TableRow key={idx}>
                                                <TableCell>
                                                    <div className="font-medium">{item.title}</div>
                                                    {item.parties.length > 0 && (
                                                        <div className="text-xs text-muted-foreground">
                                                            Parties: {item.parties.join(", ")}
                                                        </div>
                                                    )}
                                                </TableCell>
                                                <TableCell>{item.category}</TableCell>
                                                <TableCell className="max-w-md">
                                                    <div className="text-sm">{item.key_terms}</div>
                                                </TableCell>
                                                <TableCell>{getRiskBadge(item.risk_level)}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>
                    </>
                )}

                {!schedule && !generating && (
                    <div className="text-center py-12 text-muted-foreground">
                        <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>Select a schedule type and click Generate to create a disclosure schedule.</p>
                    </div>
                )}
            </main>
        </div>
    );
}
