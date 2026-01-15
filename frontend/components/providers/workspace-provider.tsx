/**
 * Workspace Provider
 * ------------------
 * Global state for:
 * - Current active workspace (scoped isolation).
 * - Document lists & Counts.
 * - Docling ingestion trigger (via refreshDocs).
 * 
 * Persists selected workspace to LocalStorage.
 */
"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { listDocs } from "@/lib/api";
import { Doc, Workspace } from "@/lib/types";

// Hardcoded for pilot
const WORKSPACES: Workspace[] = [
    { id: "Main", label: "Main Workspace" },
    { id: "Isolation", label: "Isolation Zone" },
    { id: "Finance", label: "Finance Dept" },
];

interface WorkspaceContextType {
    workspace: Workspace; // Deprecated but kept for compat
    selectedWorkspace: string;
    setSelectedWorkspace: (id: string) => void;
    workspaces: Workspace[];
    availableWorkspaces: Workspace[]; // Backward compat
    docs: Doc[];
    refreshDocs: () => Promise<void>;
    workspaceCounts: Record<string, number>;
    uploadStatus: { isUploading: boolean; fileName?: string };
    setUploadStatus: (status: { isUploading: boolean; fileName?: string }) => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
    const [workspace, setWorkspace] = useState<Workspace>(WORKSPACES[0]);
    const [docs, setDocs] = useState<Doc[]>([]);
    const [workspaceCounts, setWorkspaceCounts] = useState<Record<string, number>>({});
    const [uploadStatus, setUploadStatus] = useState<{ isUploading: boolean; fileName?: string }>({ isUploading: false });

    // Load workspace from local storage
    useEffect(() => {
        const stored = localStorage.getItem("workspace_id");
        if (stored) {
            const found = WORKSPACES.find((w) => w.id === stored);
            if (found) setWorkspace(found);
        }
    }, []);

    // Fetch counts for ALL workspaces
    const refreshCounts = async () => {
        const counts: Record<string, number> = {};
        await Promise.all(WORKSPACES.map(async (w) => {
            try {
                const docsList = await listDocs(w.id);
                counts[w.id] = docsList.length;
            } catch (e) {
                console.error(`Failed to count docs for ${w.id}`, e);
                counts[w.id] = 0;
            }
        }));
        setWorkspaceCounts(counts);
    };

    // Initial load of counts
    useEffect(() => {
        refreshCounts();
    }, []);

    // Load docs when workspace changes OR when we refresh counts (to keep sync)
    const refreshDocs = async () => {
        try {
            // Update current docs
            const docsList = await listDocs(workspace.id);
            if (docsList) {
                setDocs(docsList);
                // Also update the count for *this* workspace in our cache
                setWorkspaceCounts(prev => ({
                    ...prev,
                    [workspace.id]: docsList.length
                }));
            } else {
                setDocs([]);
            }
        } catch (e) {
            console.error("Failed to load docs", e);
            setDocs([]);
        }
    };

    useEffect(() => {
        refreshDocs();
    }, [workspace.id]);

    const handleSetWorkspace = (id: string) => {
        const w = WORKSPACES.find(x => x.id === id);
        if (w) {
            setWorkspace(w);
            localStorage.setItem("workspace_id", w.id);
        }
    };

    return (
        <WorkspaceContext.Provider
            value={{
                workspace,
                selectedWorkspace: workspace.id,
                setSelectedWorkspace: handleSetWorkspace,
                workspaces: WORKSPACES,
                availableWorkspaces: WORKSPACES, // Backward compat
                docs,
                refreshDocs,
                workspaceCounts,
                uploadStatus,
                setUploadStatus
            }}
        >
            {children}
        </WorkspaceContext.Provider>
    );
}

export function useWorkspace() {
    const context = useContext(WorkspaceContext);
    if (!context) throw new Error("useWorkspace must be used within WorkspaceProvider");
    return context;
}

