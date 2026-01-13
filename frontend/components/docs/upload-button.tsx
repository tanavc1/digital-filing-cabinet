"use client";

import { useState, useRef } from "react";
import { Upload, Loader2, FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { ingestFile } from "@/lib/api";
// import { useToast } from "@/components/ui/use-toast"; 
// Standard shadcn toast requires installing. I'll rely on simple alert or local state for pilot if toast missing.
// Actually `npx shadcn@latest add toast` wasn't run.
// I'll skip toast for now and use simple loading/error state.

export function UploadButton({ onUploadComplete }: { onUploadComplete: () => void }) {
    const { workspace } = useWorkspace();
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            setUploading(true);
            try {
                await ingestFile(file, workspace.id);
                onUploadComplete();
                if (fileInputRef.current) fileInputRef.current.value = "";
            } catch (err) {
                console.error("Upload failed", err);
                alert("Upload failed! Check console.");
            } finally {
                setUploading(false);
            }
        }
    };

    return (
        <>
            <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                onChange={handleFileChange}
                accept=".pdf,.docx,.pptx,.txt"
            />
            <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="gap-2"
            >
                {uploading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    <FileUp className="w-4 h-4" />
                )}
                {uploading ? "Ingesting..." : "Upload Document"}
            </Button>
        </>
    );
}
