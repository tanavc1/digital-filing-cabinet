"use client";

import { useEffect, useState } from "react";
import { getRiskStats, RiskStats } from "@/lib/api";
import { RiskPieChart, TypeBarChart } from "@/components/dashboard/risk-charts";
import { AlertCircle, FileText, Folder, ShieldAlert, CheckCircle, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function DashboardPage() {
    const [stats, setStats] = useState<RiskStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const workspaceId = "default";

    useEffect(() => {
        loadStats();
    }, []);

    async function loadStats() {
        try {
            setLoading(true);
            setError(null);
            const data = await getRiskStats(workspaceId);
            setStats(data);
        } catch (err) {
            console.error(err);
            setError("Failed to connect to backend. Make sure the server is running.");
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex h-screen flex-col items-center justify-center p-8 space-y-4">
                <AlertCircle className="h-12 w-12 text-red-500" />
                <h2 className="text-xl font-semibold">Connection Error</h2>
                <p className="text-muted-foreground text-center max-w-md">{error}</p>
                <Button onClick={loadStats} variant="outline">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                </Button>
            </div>
        );
    }

    if (!stats) return <div className="p-8">No data available.</div>;


    return (
        <div className="flex h-screen flex-col bg-slate-50/50">
            {/* Header */}
            <header className="flex h-14 items-center gap-4 border-b bg-white px-6 shadow-sm">
                <h1 className="font-semibold text-lg">Risk Intelligence Dashboard</h1>
            </header>

            <main className="flex-1 overflow-auto p-6 space-y-6">
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                    {/* KPI Cards */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
                            <FileText className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stats.total_docs}</div>
                            <p className="text-xs text-muted-foreground">Indexed in Data Room</p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">High Risk Items</CardTitle>
                            <ShieldAlert className="h-4 w-4 text-red-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-red-600">{stats.risk_counts["High"] || 0}</div>
                            <p className="text-xs text-muted-foreground">Require immediate attention</p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Medium Risk</CardTitle>
                            <AlertCircle className="h-4 w-4 text-amber-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-amber-600">{stats.risk_counts["Medium"] || 0}</div>
                            <p className="text-xs text-muted-foreground">Standard review needed</p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Clean / Low Risk</CardTitle>
                            <CheckCircle className="h-4 w-4 text-green-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-green-600">
                                {(stats.risk_counts["Low"] || 0) + (stats.risk_counts["Clean"] || 0)}
                            </div>
                            <p className="text-xs text-muted-foreground">Safe to proceed</p>
                        </CardContent>
                    </Card>
                </div>

                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
                    {/* Charts */}
                    <Card className="col-span-4 shadow-sm">
                        <CardHeader>
                            <CardTitle>Risk Distribution</CardTitle>
                            <CardDescription>Breakdown of documents by risk assessment</CardDescription>
                        </CardHeader>
                        <CardContent className="pl-2">
                            <RiskPieChart data={stats.risk_counts} />
                        </CardContent>
                    </Card>

                    <Card className="col-span-3 shadow-sm">
                        <CardHeader>
                            <CardTitle>Top Document Types</CardTitle>
                            <CardDescription>Volume by category</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <TypeBarChart data={stats.type_counts} />
                        </CardContent>
                    </Card>
                </div>

                {/* Heatmap List */}
                <Card className="shadow-sm">
                    <CardHeader>
                        <CardTitle>Folder Risk Heatmap</CardTitle>
                        <CardDescription>Identify areas with concentrated risk (e.g. specific deal folders)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-1">
                            {Object.entries(stats.folder_risks)
                                .sort((a, b) => b[1].High - a[1].High) // Sort by High Risk count desc
                                .slice(0, 10) // Top 10 only
                                .map(([path, val]) => (
                                    <div key={path} className="flex items-center justify-between py-3 px-2 border-b last:border-0 hover:bg-slate-50 transition-colors rounded-sm">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-full ${val.High > 0 ? "bg-red-50" : "bg-blue-50"}`}>
                                                <Folder className={`h-4 w-4 ${val.High > 0 ? "text-red-500" : "text-blue-500"}`} />
                                            </div>
                                            <span className="font-medium text-sm text-slate-700">{path}</span>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <span className="text-xs text-gray-500">{val.total} docs</span>
                                            {val.High > 0 ? (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                                    {val.High} High Risk
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                    Safe
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            {Object.values(stats.folder_risks).every(v => v.High === 0) && (
                                <div className="text-center py-8 text-gray-500">No high risk folders detected.</div>
                            )}

                            {Object.keys(stats.folder_risks).length === 0 && (
                                <div className="text-center py-8 text-gray-500">No folders found. Upload some documents!</div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </main>
        </div>
    );
}
