import axios from "axios";
import { Doc, QueryResult } from "./types";

const API_Base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
    baseURL: API_Base,
});

export const listDocs = async (workspaceId: string): Promise<Doc[]> => {
    const res = await api.get("/documents", {
        params: { workspace_id: workspaceId },
    });
    return res.data.documents || [];
};

export const deleteDoc = async (docId: string, workspaceId: string): Promise<void> => {
    await api.delete(`/documents/${docId}`, {
        params: { workspace_id: workspaceId },
    });
};

export const ingestFile = async (
    file: File,
    workspaceId: string,
    onUploadProgress?: (progressEvent: any) => void
): Promise<{ doc_id: string; status: string }> => {
    const formData = new FormData();
    formData.append("file", file);

    // Note: Backend endpoint for multipart might be /ingest/any or similar. 
    // Assuming /ingest/any based on original code. 
    // If backend only has /ingest/text, this needs update. 
    // But for now, restoring original logic for upload.
    const res = await api.post("/ingest/any", formData, {
        params: { workspace_id: workspaceId },
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress,
    });
    return res.data;
};

export const queryDocs = async (
    q: string,
    workspaceId: string,
    docIds?: string[]
): Promise<QueryResult> => {
    const payload: any = {
        q,
        workspace_id: workspaceId,
    };

    if (docIds && docIds.length > 0) {
        payload.doc_ids = docIds;
    }

    const res = await api.post("/query", payload);
    return res.data;
};

export const getDocContent = async (docId: string, workspaceId: string): Promise<{ text: string }> => {
    const res = await api.get(`/documents/${docId}/content`, {
        params: { workspace_id: workspaceId }
    });
    return res.data;
};
