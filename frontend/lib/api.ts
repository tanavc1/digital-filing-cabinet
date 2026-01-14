import axios from "axios";
import { Doc, QueryResult } from "./types";

const API_Base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
    baseURL: API_Base,
});

// Inject API Secret if configured (for Pilot security)
api.interceptors.request.use((config) => {
    const secret = process.env.NEXT_PUBLIC_API_SECRET;
    if (secret) {
        config.headers["X-API-Key"] = secret;
    }
    return config;
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

export interface ZipIngestResult {
    status: string;
    total_files: number;
    ingested: number;
    skipped: number;
    errors: string[];
    doc_ids: string[];
}

export const ingestZip = async (
    file: File,
    workspaceId: string,
    options?: { enableOcr?: boolean; enableVision?: boolean }
): Promise<ZipIngestResult> => {
    const formData = new FormData();
    formData.append("file", file);

    const params: any = {
        workspace_id: workspaceId,
        enable_ocr: options?.enableOcr || false,
        enable_vision: options?.enableVision || false
    };

    const res = await api.post("/ingest/zip", formData, {
        params,
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 600000, // 10 minute timeout for large ZIPs
    });
    return res.data;
};

// ----------------------------
// Audit API
// ----------------------------

export interface AuditTemplate {
    id: string;
    name: string;
    description: string;
    question_count: number;
}

export interface AuditCitation {
    doc_id: string;
    quote: string;
    chunk_id?: string;
}

export interface AuditFinding {
    question: string;
    answer: string;
    status: "FOUND" | "NOT_FOUND" | "UNCLEAR" | "ERROR";
    severity: "HIGH" | "MEDIUM" | "LOW" | "INFO";
    category: string;
    citations: AuditCitation[];
}

export interface AuditResult {
    audit_id: string;
    template_name?: string;
    folder_path?: string;
    findings: AuditFinding[];
    summary: {
        found: number;
        not_found: number;
        unclear: number;
        errors: number;
        high_risk: number;
    };
}

export const listAuditTemplates = async (): Promise<AuditTemplate[]> => {
    const res = await api.get("/audit/templates");
    return res.data.templates || [];
};

export const runAudit = async (
    workspaceId: string,
    templateId?: string,
    folderPath?: string | null,
    customQuestions?: string[]
): Promise<AuditResult> => {
    const res = await api.post("/audit/run", {
        workspace_id: workspaceId,
        template_id: templateId,
        folder_path: folderPath || null,
        custom_questions: customQuestions
    }, {
        timeout: 300000  // 5 minute timeout for large audits
    });
    return res.data;
};
