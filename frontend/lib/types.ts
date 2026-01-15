export interface Workspace {
    id: string;
    label: string;
}

export interface Doc {
    doc_id: string;
    title: string;
    source: string;
    created_at: number;
    modified_at: number;
    uri?: string;
    folder_path?: string;
    summary_text?: string;
    doc_type?: string;   // [NEW] e.g. "Lease", "NDA"
    risk_level?: string; // [NEW] e.g. "High", "Clean"
}

export interface Evidence {
    evidence_id?: string;
    doc_id: string;
    workspace_id: string;
    quote: string;
    start_char: number;
    end_char: number;
    verified: boolean;
    confidence: number;
    chunk_id?: string;
}

export interface ClosestMention {
    doc_id: string;
    chunk_id: string;
    excerpt: string;
    rerank_score: number;
}

export interface QueryResult {
    answer: string;
    abstained: boolean;
    sources: Evidence[];
    closest_mentions: ClosestMention[];
    explanation?: string;
}

export type ScopeType = "all" | "selected";
