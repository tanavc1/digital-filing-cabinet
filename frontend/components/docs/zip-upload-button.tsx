"use client";

import { useState, useRef } from "react";
import { FolderArchive, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { ingestZip, ZipIngestResult } from "@/lib/api";
import { toast } from "sonner";

export function ZipUploadButton({ onUploadComplete }: { onUploadComplete: () => void }) {
    const { workspace, setUploadStatus } = useWorkspace();
    const [isProcessing, setIsProcessing] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;

        const file = e.target.files[0];

        if (!file.name.toLowerCase().endsWith('.zip')) {
            toast.error("Please select a ZIP file");
            return;
        }

        setIsProcessing(true);
        setUploadStatus({ isUploading: true, fileName: file.name });
        toast.info(`Uploading Data Room: ${file.name}...`);

        try {
            const result: ZipIngestResult = await ingestZip(file, workspace.id, {
                enableVision: true
            });

            if (result.ingested > 0) {
                toast.success(
                    `Data Room uploaded! ${result.ingested} files ingested` +
                    (result.skipped > 0 ? `, ${result.skipped} skipped` : "") +
                    (result.errors.length > 0 ? `, ${result.errors.length} errors` : "")
                );
            } else if (result.errors.length > 0) {
                toast.error(`Upload failed: ${result.errors[0]}`);
            } else {
                toast.warning("No supported files found in ZIP");
            }

            onUploadComplete();
        } catch (err: any) {
            console.error("ZIP upload failed:", err);
            toast.error(err?.response?.data?.detail || "Failed to upload Data Room");
        } finally {
            setIsProcessing(false);
            setUploadStatus({ isUploading: false });
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    return (
        <div>
            <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                onChange={handleFileChange}
                accept=".zip"
            />
            <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={isProcessing}
                variant="outline"
                className="gap-2 cursor-pointer"
            >
                {isProcessing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    <FolderArchive className="w-4 h-4" />
                )}
                {isProcessing ? "Processing..." : "Upload Data Room"}
            </Button>
        </div>
    );
}
