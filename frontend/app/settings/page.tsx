"use client";

import { useEffect, useState } from "react";
import { Settings, Wifi, WifiOff, Server, CheckCircle, XCircle, Loader2, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";

interface ModeStatus {
    offline_mode: boolean;
    llm_provider: string;
    ollama_available: boolean;
    ollama_host: string;
}

export default function SettingsPage() {
    const [status, setStatus] = useState<ModeStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [toggling, setToggling] = useState(false);

    useEffect(() => {
        loadStatus();
    }, []);

    async function loadStatus() {
        try {
            setLoading(true);
            const res = await api.get("/settings/mode");
            setStatus(res.data);
        } catch (err) {
            console.error("Failed to load settings:", err);
        } finally {
            setLoading(false);
        }
    }

    async function toggleMode() {
        if (!status) return;

        try {
            setToggling(true);
            await api.post(`/settings/mode?offline=${!status.offline_mode}`);
            // Reload status
            await loadStatus();
        } catch (err) {
            console.error("Failed to toggle mode:", err);
        } finally {
            setToggling(false);
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
            <header className="flex h-14 items-center border-b bg-white px-6 shadow-sm">
                <Settings className="h-5 w-5 mr-2" />
                <h1 className="font-semibold text-lg">Settings</h1>
            </header>

            <main className="flex-1 overflow-auto p-6 space-y-6 max-w-3xl">
                {/* Connection Mode */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            {status?.offline_mode ? (
                                <WifiOff className="h-5 w-5 text-amber-500" />
                            ) : (
                                <Wifi className="h-5 w-5 text-green-500" />
                            )}
                            Connection Mode
                        </CardTitle>
                        <CardDescription>
                            Control whether the application uses local AI (Ollama) or cloud services (OpenAI).
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between p-4 border rounded-lg">
                            <div className="space-y-0.5">
                                <Label className="text-base">Offline Mode</Label>
                                <p className="text-sm text-muted-foreground">
                                    When enabled, all AI processing happens locally. Your data never leaves your machine.
                                </p>
                            </div>
                            <Switch
                                checked={status?.offline_mode || false}
                                onCheckedChange={toggleMode}
                                disabled={toggling}
                            />
                        </div>

                        <div className="grid gap-4">
                            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                                <span className="text-sm font-medium">Current LLM Provider</span>
                                <Badge variant="outline" className="font-mono">
                                    {status?.llm_provider || "unknown"}
                                </Badge>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Ollama Status */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Server className="h-5 w-5" />
                            Local AI Server (Ollama)
                        </CardTitle>
                        <CardDescription>
                            Status of your local Ollama installation for offline AI processing.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between p-4 border rounded-lg">
                            <div className="flex items-center gap-3">
                                {status?.ollama_available ? (
                                    <CheckCircle className="h-5 w-5 text-green-500" />
                                ) : (
                                    <XCircle className="h-5 w-5 text-red-500" />
                                )}
                                <div>
                                    <div className="font-medium">
                                        {status?.ollama_available ? "Connected" : "Not Available"}
                                    </div>
                                    <div className="text-sm text-muted-foreground">
                                        {status?.ollama_host}
                                    </div>
                                </div>
                            </div>
                            <Button variant="ghost" size="sm" onClick={loadStatus}>
                                <RefreshCw className="h-4 w-4" />
                            </Button>
                        </div>

                        {!status?.ollama_available && (
                            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                                <h4 className="font-medium text-amber-800 mb-2">Ollama Not Detected</h4>
                                <p className="text-sm text-amber-700 mb-3">
                                    To enable offline mode, you need to install and run Ollama:
                                </p>
                                <ol className="text-sm text-amber-700 list-decimal list-inside space-y-1">
                                    <li>Install from <code className="bg-amber-100 px-1 rounded">https://ollama.ai</code></li>
                                    <li>Run <code className="bg-amber-100 px-1 rounded">ollama serve</code></li>
                                    <li>Pull models: <code className="bg-amber-100 px-1 rounded">ollama pull llama3</code></li>
                                </ol>
                            </div>
                        )}

                        {status?.ollama_available && (
                            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                                <h4 className="font-medium text-green-800 mb-1">✓ Ready for Offline Use</h4>
                                <p className="text-sm text-green-700">
                                    Your local AI server is running. Enable Offline Mode above to process all documents locally.
                                </p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Data Privacy Notice */}
                <Card>
                    <CardHeader>
                        <CardTitle>Data Privacy</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3 text-sm text-muted-foreground">
                            <p>
                                <strong className="text-foreground">Offline Mode:</strong> All document processing,
                                AI analysis, and search happens entirely on your local machine. No data is sent to
                                external servers.
                            </p>
                            <p>
                                <strong className="text-foreground">Online Mode:</strong> Document content may be
                                sent to OpenAI's API for processing. OpenAI's data usage policies apply.
                            </p>
                            <p>
                                Regardless of mode, your documents are stored locally in a LanceDB database on your machine.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </main>
        </div>
    );
}
