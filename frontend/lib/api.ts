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
    onUploadProgress?: (progressEvent: any) => void,
    folderPath?: string // [NEW] relative folder path
): Promise<{ doc_id: string; status: string }> => {
    const formData = new FormData();
    formData.append("file", file);

    // Determine if this is an image file
    const isImage = file.type.startsWith("image/") ||
        /\.(png|jpg|jpeg|gif|webp|bmp)$/i.test(file.name);

    // Use appropriate endpoint
    const endpoint = isImage ? "/ingest/image" : "/ingest/any";

    // For PDFs, enable vision by default to analyze charts/images
    const params: any = {
        workspace_id: workspaceId,
        folder_path: folderPath || "/" // [NEW] Pass folder path
    };
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

export const deleteDocument = async (docId: string, workspaceId: string): Promise<{ status: string }> => {
    const res = await api.delete(`/documents/${docId}`, {
        params: { workspace_id: workspaceId }
    });
    return res.data;
};

export const getDocument = async (docId: string, workspaceId: string): Promise<any> => {
    const res = await api.get(`/documents/${docId}`, {
        params: { workspace_id: workspaceId }
    });
    return res.data;
};

export const getDocumentContent = async (docId: string, workspaceId: string): Promise<{ content: string }> => {
    const res = await api.get(`/documents/${docId}/content`, {
        params: { workspace_id: workspaceId }
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

// ----------------------------
// Document Comparison API
// ----------------------------

export interface DifferenceItem {
    category: string;
    description: string;
    severity: "HIGH" | "MEDIUM" | "LOW";
    original_text?: string;
    revised_text?: string;
}

export interface DocumentInfo {
    doc_id: string;
    title: string;
    chunk_count: number;
}

export interface CompareStats {
    total_changes: number;
    high_severity: number;
    medium_severity: number;
    low_severity: number;
}

export interface CompareResult {
    doc_a: DocumentInfo;
    doc_b: DocumentInfo;
    differences: DifferenceItem[];
    summary: string;
    stats: CompareStats;
    error?: string;
}

export const compareDocuments = async (
    docIdA: string,
    docIdB: string,
    workspaceId: string
): Promise<CompareResult> => {
    const res = await api.post("/compare", {
        doc_id_a: docIdA,
        doc_id_b: docIdB,
        workspace_id: workspaceId
    });
    return res.data;
};

// ----------------------------
// Risk Dashboard API
// ----------------------------

export interface RiskStats {
    total_docs: number;
    risk_counts: Record<string, number>;
    type_counts: Record<string, number>;
    folder_risks: Record<string, { High: number; total: number }>;
}

export const getRiskStats = async (workspaceId: string): Promise<RiskStats> => {
    const res = await api.get(`/risk/stats?workspace_id=${workspaceId}`);
    return res.data;
};

// --- Review API ---
export interface Review {
    doc_id: string;
    doc_title: string;
    doc_type: string;
    risk_level: string;
    folder_path: string;
    status: string;
    assigned_to: string | null;
    reviewer_notes: string;
    confidence: number;
}

export const getReviews = async (workspaceId: string, filters?: { status?: string; assigned_to?: string }) => {
    const params = new URLSearchParams({ workspace_id: workspaceId });
    if (filters?.status) params.append("status", filters.status);
    if (filters?.assigned_to) params.append("assigned_to", filters.assigned_to);
    const res = await api.get(`/reviews?${params.toString()}`);
    return res.data;
};

export const updateReview = async (docId: string, update: { status?: string; assigned_to?: string; reviewer_notes?: string }) => {
    const res = await api.put(`/reviews/${docId}`, update);
    return res.data;
};

export const bulkAssignReviews = async (docIds: string[], assignedTo: string) => {
    const res = await api.post("/reviews/bulk-assign", { doc_ids: docIds, assigned_to: assignedTo });
    return res.data;
};

export const bulkUpdateStatus = async (docIds: string[], status: string) => {
    const res = await api.post("/reviews/bulk-status", { doc_ids: docIds, status });
    return res.data;
};

// --- Playbook/Clause API ---
export interface Playbook {
    id: string;
    name: string;
    description: string;
    doc_types: string[];
    clause_types: string[];
}

export interface ClauseExtraction {
    id: string;
    doc_id: string;
    doc_title: string;
    clause_type: string;
    extracted_value: string;
    snippet: string;
    page_number: number;
    confidence: number;
    verified: boolean;
    flagged: boolean;
}

export const getPlaybooks = async () => {
    const res = await api.get("/playbooks");
    return res.data;
};

export const runPlaybook = async (playbookId: string, workspaceId: string, docIds?: string[]) => {
    const res = await api.post(`/playbooks/${playbookId}/run`, { workspace_id: workspaceId, doc_ids: docIds }, { timeout: 600000 });
    return res.data;
};

export const getClauseMatrix = async (workspaceId: string) => {
    const res = await api.get(`/clauses/matrix?workspace_id=${workspaceId}`);
    return res.data;
};

export const getClause = async (clauseId: string) => {
    const res = await api.get(`/clauses/${clauseId}`);
    return res.data;
};

export const updateClause = async (clauseId: string, update: { verified?: boolean; flagged?: boolean }) => {
    const params = new URLSearchParams();
    if (update.verified !== undefined) params.append("verified", String(update.verified));
    if (update.flagged !== undefined) params.append("flagged", String(update.flagged));
    const res = await api.put(`/clauses/${clauseId}?${params.toString()}`);
    return res.data;
};

// --- Issues API ---
export interface Issue {
    id: string;
    title: string;
    description: string;
    severity: string;
    status: string;
    doc_id: string | null;
    doc_title: string | null;
    clause_id: string | null;
    owner: string | null;
    action_required: string;
    created_at: string;
}

export const getIssues = async (filters?: { severity?: string; status?: string; owner?: string }) => {
    const params = new URLSearchParams();
    if (filters?.severity) params.append("severity", filters.severity);
    if (filters?.status) params.append("status", filters.status);
    if (filters?.owner) params.append("owner", filters.owner);
    const res = await api.get(`/issues?${params.toString()}`);
    return res.data;
};

export const createIssue = async (issue: Partial<Issue>) => {
    const res = await api.post("/issues", issue);
    return res.data;
};

export const updateIssue = async (issueId: string, update: Partial<Issue>) => {
    const res = await api.put(`/issues/${issueId}`, update);
    return res.data;
};

export const deleteIssue = async (issueId: string) => {
    const res = await api.delete(`/issues/${issueId}`);
    return res.data;
};

export default api;

