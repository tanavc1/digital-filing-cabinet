"use client";

import { useEffect, useState } from "react";
import { Settings, Wifi, WifiOff, Server, CheckCircle, XCircle, Loader2, RefreshCw, Cpu, Eye, Brain, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";

interface ModeStatus {
    offline_mode: boolean;
    llm_provider: string;
    vision_provider: string;
    ollama_available: boolean;
    ollama_host: string;
    llm_model: string;
    vision_model: string;
    embed_model: string;
    rerank_model: string;
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

    const isLocal = status?.llm_provider === "ollama";

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
                            {isLocal ? (
                                <WifiOff className="h-5 w-5 text-amber-500" />
                            ) : (
                                <Wifi className="h-5 w-5 text-green-500" />
                            )}
                            AI Provider Mode
                        </CardTitle>
                        <CardDescription>
                            Switch between local AI models (private, offline) and cloud APIs (faster, requires API keys).
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between p-4 border rounded-lg">
                            <div className="space-y-0.5">
                                <Label className="text-base">Local-First Mode</Label>
                                <p className="text-sm text-muted-foreground">
                                    When enabled, all AI runs on your machine via Ollama. No data leaves your computer.
                                </p>
                            </div>
                            <Switch
                                checked={status?.offline_mode || false}
                                onCheckedChange={toggleMode}
                                disabled={toggling}
                            />
                        </div>

                        <div className="grid gap-3">
                            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                                <span className="text-sm font-medium">LLM Provider</span>
                                <Badge variant={isLocal ? "secondary" : "default"} className="font-mono">
                                    {status?.llm_provider || "unknown"}
                                </Badge>
                            </div>
                            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                                <span className="text-sm font-medium">Vision Provider</span>
                                <Badge variant={status?.vision_provider === "ollama" ? "secondary" : "default"} className="font-mono">
                                    {status?.vision_provider || "unknown"}
                                </Badge>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Active Models */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Brain className="h-5 w-5" />
                            Active Models
                        </CardTitle>
                        <CardDescription>
                            The AI models currently powering your search and analysis.
                            {isLocal && " All running locally on your machine."}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid gap-3">
                            <div className="flex items-center justify-between p-3 border rounded-lg">
                                <div className="flex items-center gap-2">
                                    <Cpu className="h-4 w-4 text-blue-500" />
                                    <div>
                                        <div className="text-sm font-medium">Text LLM</div>
                                        <div className="text-xs text-muted-foreground">Answer generation & evidence extraction</div>
                                    </div>
                                </div>
                                <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">
                                    {status?.llm_model}
                                </code>
                            </div>

                            <div className="flex items-center justify-between p-3 border rounded-lg">
                                <div className="flex items-center gap-2">
                                    <Eye className="h-4 w-4 text-purple-500" />
                                    <div>
                                        <div className="text-sm font-medium">Vision LLM</div>
                                        <div className="text-xs text-muted-foreground">Chart, diagram & image analysis</div>
                                    </div>
                                </div>
                                <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">
                                    {status?.vision_model}
                                </code>
                            </div>

                            <div className="flex items-center justify-between p-3 border rounded-lg">
                                <div className="flex items-center gap-2">
                                    <Layers className="h-4 w-4 text-green-500" />
                                    <div>
                                        <div className="text-sm font-medium">Embeddings</div>
                                        <div className="text-xs text-muted-foreground">Semantic search vectors (always local)</div>
                                    </div>
                                </div>
                                <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">
                                    {status?.embed_model}
                                </code>
                            </div>

                            <div className="flex items-center justify-between p-3 border rounded-lg">
                                <div className="flex items-center gap-2">
                                    <Layers className="h-4 w-4 text-orange-500" />
                                    <div>
                                        <div className="text-sm font-medium">Reranker</div>
                                        <div className="text-xs text-muted-foreground">Result quality scoring (always local)</div>
                                    </div>
                                </div>
                                <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">
                                    {status?.rerank_model}
                                </code>
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
                            Ollama runs the text and vision LLMs locally on your machine.
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
                                    To use local AI models, install and start Ollama:
                                </p>
                                <ol className="text-sm text-amber-700 list-decimal list-inside space-y-1">
                                    <li>Install from <code className="bg-amber-100 px-1 rounded">https://ollama.com</code></li>
                                    <li>Pull text model: <code className="bg-amber-100 px-1 rounded">ollama pull phi4-mini</code></li>
                                    <li>Pull vision model: <code className="bg-amber-100 px-1 rounded">ollama pull qwen3-vl:8b</code></li>
                                </ol>
                            </div>
                        )}

                        {status?.ollama_available && (
                            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                                <h4 className="font-medium text-green-800 mb-1">✓ Local AI Ready</h4>
                                <p className="text-sm text-green-700">
                                    Ollama is running. All AI processing happens on your machine — your data never leaves.
                                </p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Cloud API Keys (Optional) */}
                <Card>
                    <CardHeader>
                        <CardTitle>Cloud Providers (Optional)</CardTitle>
                        <CardDescription>
                            If you prefer cloud LLMs for faster responses, configure API keys in your <code className="bg-slate-100 px-1 rounded text-xs">.env</code> file.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3 text-sm text-muted-foreground">
                            <div className="p-3 bg-slate-50 rounded-lg space-y-1">
                                <div className="font-medium text-foreground">OpenAI (Text LLM)</div>
                                <p>Set <code className="bg-white px-1 rounded text-xs">LLM_PROVIDER=openai</code> and <code className="bg-white px-1 rounded text-xs">OPENAI_API_KEY=sk-...</code> in your <code className="bg-white px-1 rounded text-xs">.env</code></p>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-lg space-y-1">
                                <div className="font-medium text-foreground">Google Gemini (Vision)</div>
                                <p>Set <code className="bg-white px-1 rounded text-xs">VISION_PROVIDER=gemini</code> and <code className="bg-white px-1 rounded text-xs">GEMINI_API_KEY=AIza...</code> in your <code className="bg-white px-1 rounded text-xs">.env</code></p>
                            </div>
                        </div>
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
                                <strong className="text-foreground">Local Mode (default):</strong> All document processing,
                                AI analysis, and search runs entirely on your machine. Nothing is sent to external servers.
                            </p>
                            <p>
                                <strong className="text-foreground">Cloud Mode:</strong> When using OpenAI or Gemini,
                                document content is sent to their APIs for processing. Their respective data policies apply.
                            </p>
                            <p>
                                Regardless of mode, your documents are always stored locally in LanceDB on your machine.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </main>
        </div>
    );
}
