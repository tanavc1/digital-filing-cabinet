"use client";

import { useState, useRef } from "react";
import { Upload, Loader2, FileUp, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { ingestFile } from "@/lib/api";
import { toast } from "sonner";

interface UploadProgress {
    fileName: string;
    status: "pending" | "uploading" | "complete" | "error";
    progress: number;
    error?: string;
}

export function UploadButton({ onUploadComplete }: { onUploadComplete: () => void }) {
    const { workspace } = useWorkspace();
    const [queue, setQueue] = useState<UploadProgress[]>([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;

        const files = Array.from(e.target.files);

        // Initialize queue
        const newQueue: UploadProgress[] = files.map((file) => ({
            fileName: file.name,
            status: "pending",
            progress: 0,
        }));

        setQueue(newQueue);
        setIsProcessing(true);

        // Process files sequentially
        for (let i = 0; i < files.length; i++) {
            const file = files[i];

            // Update status to uploading
            setQueue((prev) =>
                prev.map((item, idx) =>
                    idx === i ? { ...item, status: "uploading" } : item
                )
            );

            try {
                // Simulate progress increments
                const progressInterval = setInterval(() => {
                    setQueue((prev) =>
                        prev.map((item, idx) =>
                            idx === i && item.progress < 90
                                ? { ...item, progress: Math.min(90, item.progress + 10) }
                                : item
                        )
                    );
                }, 500);

                // Extract folder path if active (e.g. from drag-drop or directory selection)
                const relPath = (file as any).webkitRelativePath;
                const folderPath = relPath ? "/" + relPath.substring(0, relPath.lastIndexOf("/")) : "/";

                await ingestFile(file, workspace.id, undefined, folderPath);

                clearInterval(progressInterval);

                // Mark as complete
                setQueue((prev) =>
                    prev.map((item, idx) =>
                        idx === i
                            ? { ...item, status: "complete", progress: 100 }
                            : item
                    )
                );

                toast.success(`${file.name} uploaded successfully`);
            } catch (err) {
                // Mark as error
                setQueue((prev) =>
                    prev.map((item, idx) =>
                        idx === i
                            ? {
                                ...item,
                                status: "error",
                                error: err instanceof Error ? err.message : "Upload failed",
                            }
                            : item
                    )
                );

                toast.error(`Failed to upload ${file.name}`);
                console.error("Upload failed", err);
            }
        }

        // Cleanup
        setIsProcessing(false);
        onUploadComplete();
        if (fileInputRef.current) fileInputRef.current.value = "";

        // Clear queue after 3 seconds
        setTimeout(() => setQueue([]), 3000);
    };

    const hasActiveUploads = queue.some((item) => item.status === "uploading" || item.status === "pending");

    return (
        <div className="relative">
            <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                onChange={handleFileChange}
                accept=".pdf,.docx,.pptx,.txt,.png,.jpg,.jpeg,.gif,.webp"
                multiple
            />
            <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={isProcessing}
                className="gap-2 cursor-pointer"
            >
                {isProcessing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    <FileUp className="w-4 h-4" />
                )}
                {isProcessing ? "Uploading..." : "Upload Documents"}
            </Button>

            {/* Progress overlay */}
            {queue.length > 0 && (
                <div className="absolute top-full right-0 mt-2 w-80 max-h-96 overflow-auto bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-lg z-50 p-3 space-y-2">
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-semibold">Upload Progress</h4>
                        <button
                            onClick={() => setQueue([])}
                            className="text-zinc-500 hover:text-zinc-700"
                            disabled={hasActiveUploads}
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>

                    {queue.map((item, idx) => (
                        <div key={idx} className="space-y-1">
                            <div className="flex items-center justify-between text-xs">
                                <span className="truncate flex-1 mr-2">{item.fileName}</span>
                                <span className="text-zinc-500">
                                    {item.status === "complete" && "✓"}
                                    {item.status === "error" && "✗"}
                                    {item.status === "uploading" && `${item.progress}%`}
                                    {item.status === "pending" && "Pending"}
                                </span>
                            </div>

                            {(item.status === "uploading" || item.status === "pending") && (
                                <div className="w-full bg-zinc-200 dark:bg-zinc-800 rounded-full h-1.5">
                                    <div
                                        className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                                        style={{ width: `${item.progress}%` }}
                                    />
                                </div>
                            )}

                            {item.status === "error" && item.error && (
                                <p className="text-xs text-red-600">{item.error}</p>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
