# Evidence-Grade RAG System

This system implements a strict, court-admissible RAG pipeline designed to eliminate hallucinations and provide audit-grade answers.

## Architecture

### 1. Retrieval (Hybrid + Rerank)
Standard retrieval pipeline (BM25 + LanceDB Vector + RRF + Cross-Encoder Reranking) identifies the top 5 most relevant chunks.

### 2. Evidence Windows
For each top chunk, we automatically fetch the **neighboring chunks** (previous and next) from the same document. This creates an "Evidence Window" that preserves context, fixing issues with split bullet points or headers separated from content.

### 3. Two-Step LLM Pipeline
Instead of a single generation call, we use two strict, separate steps:

#### Step 1: Evidence Extraction (The Auditor)
- **Input**: Question + Evidence Windows.
- **Task**: Extract VERBATIM quotes only. No thinking, no summarizing.
- **Output**: JSON containing the exact quotes and their document IDs.
- **Fail State**: If no exact evidence exists, it returns `NO_EVIDENCE`.

#### Step 2: Answer Synthesis (The Judge)
- **Input**: Question + Extracted Verbatim Evidence (from Step 1).
- **Task**: Write the answer using *only* the provided quotes.
- **Output**: The final answer text.

### 4. Abstention
If Step 1 returns `NO_EVIDENCE`, the system halts and returns a standard "Not found in the document" response with an explanation, rather than attempting to hallucinate an answer.

## Verification
Run `python3 verify_evidence.py` to test:
1.  **Exact Quote**: Verifies character-perfect extraction.
2.  **Multi-Chunk**: Verifies answers spanning multiple chunks.
3.  **PPTX Bullets**: Verifies extraction of list items.
4.  **Negative**: Verifies correct abstention.
5.  **Isolation**: Verifies workspace boundaries are respected.
