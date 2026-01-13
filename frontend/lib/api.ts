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

    // Determine if this is an image file
    const isImage = file.type.startsWith("image/") ||
        /\.(png|jpg|jpeg|gif|webp|bmp)$/i.test(file.name);

    // Use appropriate endpoint
    const endpoint = isImage ? "/ingest/image" : "/ingest/any";

    // For PDFs, enable vision by default to analyze charts/images
    const params: any = { workspace_id: workspaceId };
    if (file.name.toLowerCase().endsWith(".pdf")) {
        params.enable_vision = true;
    }

    const res = await api.post(endpoint, formData, {
        params,
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
