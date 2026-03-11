"""
LLM abstraction layer for document summarization, evidence extraction,
answer synthesis, and query rewriting.
"""
import os
import json
import logging
from typing import List, Dict

from core.config import Config
from llm_providers import get_llm_provider, LLMProvider
from prompts import (
    SUMMARIZE_DOC_PROMPT,
    EXTRACT_EVIDENCE_SINGLE_SYSTEM,
    EXTRACT_EVIDENCE_BATCHED_SYSTEM,
    SYNTHESIZE_ANSWER_SYSTEM,
    REWRITE_QUERY_SYSTEM,
)


logger = logging.getLogger("rag_lancedb")


class NanoLLM:
    """
    Async wrapper for LLM API calls.
    Handles summarization, evidence extraction, answer synthesis, and query rewriting.
    """
    def __init__(self, config: Config):
        self.config = config
        provider_type = os.getenv("LLM_PROVIDER", "ollama")
        provider_kwargs = {}
        if provider_type == "ollama":
            provider_kwargs["timeout"] = config.llm_timeout
        self.provider = get_llm_provider(
            provider_type=provider_type,
            **provider_kwargs
        )
        self.answer_only_question = config.answer_only_question

    async def summarize_doc(self, text: str, title: str = "") -> str:
        prompt = SUMMARIZE_DOC_PROMPT.format(title=title, text=text)
        return await self.provider.complete(prompt=prompt)

    async def extract_evidence_single(self, question: str, window: Dict) -> Dict:
        """
        Extract evidence from a SINGLE window.
        Async for parallel execution.
        """
        system_prompt = EXTRACT_EVIDENCE_SINGLE_SYSTEM

        block = (
            f"--- WINDOW START ---\n"
            f"Doc ID: {window['doc_id']}\n"
            f"Chunk IDs: {json.dumps(window['chunk_ids'])}\n"
            f"TEXT:\n{window['window_text']}\n"
            f"--- WINDOW END ---"
        )

        user_prompt = f"QUESTION: {question}\n\nEVIDENCE WINDOW:\n{block}"

        try:
            return await self.provider.complete_json(
                prompt=user_prompt,
                system=system_prompt
            )
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {"status": "NO_EVIDENCE", "evidence": [], "explanation": f"LLM Error: {e}"}

    async def extract_evidence(self, question: str, windows: List[Dict]) -> Dict:
        """
        Batched extraction for small N (Phase 9 Hybrid Strategy).
        Processes multiple windows in a single LLM call to reduce overhead.
        """
        if not windows:
            return {"evidence": [], "explanation": "No context provided."}

        context_blocks = []
        for i, w in enumerate(windows):
            context_blocks.append(f"Source {i+1} (Doc: {w['doc_id']}):\n{w['window_text']}")

        joined_context = "\n\n".join(context_blocks)
        system_prompt = EXTRACT_EVIDENCE_BATCHED_SYSTEM
        user_prompt = f"Question: {question}\n\nContext:\n{joined_context}"

        try:
            data = await self.provider.complete_json(
                prompt=user_prompt,
                system=system_prompt
            )
            # Handle case where LLM returns a raw list instead of {evidence: [...]}
            if isinstance(data, list):
                raw_evidence = data
                explanation = ""
            else:
                raw_evidence = data.get("evidence", [])
                explanation = data.get("explanation", "")

            # Map back doc_ids
            doc_map = {f"Source {i+1}": w["doc_id"] for i, w in enumerate(windows)}
            doc_id_set = {w["doc_id"] for w in windows}

            cleaned_evidence = []
            for item in raw_evidence:
                if isinstance(item, str):
                    item = {"quote": item, "doc_id": windows[0]["doc_id"] if windows else ""}

                d_id = item.get("doc_id")
                if d_id in doc_map:
                    d_id = doc_map[d_id]

                if d_id not in doc_id_set:
                    if len(windows) == 1:
                        d_id = windows[0]["doc_id"]
                    else:
                        continue

                item["doc_id"] = d_id
                cleaned_evidence.append(item)

            return {
                "evidence": cleaned_evidence,
                "explanation": explanation
            }

        except Exception as e:
            logger.error(f"Batched extraction failed: {e}")
            return {"evidence": [], "explanation": f"Error: {str(e)}"}

    async def synthesize_answer(self, question: str, evidence_list: List[Dict]) -> str:
        """Synthesize answer using ONLY the extracted evidence."""
        system_prompt = SYNTHESIZE_ANSWER_SYSTEM

        evidence_text = ""
        for i, item in enumerate(evidence_list):
            evidence_text += f"QUOTE {i+1}: {item['quote']}\n(Source: Doc {item.get('doc_id')})\n\n"

        user_prompt = f"QUESTION: {question}\n\nVERIFIED EVIDENCE:\n{evidence_text}"

        return await self.provider.complete(
            prompt=user_prompt,
            system=system_prompt
        )

    async def synthesize_answer_stream(self, question: str, evidence_list: List[Dict]):
        """
        Stream the answer generation token-by-token.
        Yields chunks of text.
        """
        system_prompt = SYNTHESIZE_ANSWER_SYSTEM

        evidence_text = ""
        for i, item in enumerate(evidence_list):
            evidence_text += f"QUOTE {i+1}: {item['quote']}\n(Source: Doc {item.get('doc_id')})\n\n"

        user_prompt = f"QUESTION: {question}\n\nVERIFIED EVIDENCE:\n{evidence_text}"

        async for chunk in self.provider.stream(
            prompt=user_prompt,
            system=system_prompt
        ):
            yield chunk

    async def rewrite_query(self, query: str, history: List[Dict]) -> str:
        """Rewrites the query based on conversation history."""
        if not history:
            return query

        system_prompt = REWRITE_QUERY_SYSTEM

        conversation_text = ""
        for msg in history[:-1]:
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n"

        user_prompt = (
            f"Conversation History:\n{conversation_text}\n"
            f"Last Question: {query}\n\n"
            "Rewritten Standalone Question:"
        )

        try:
            rewritten = await self.provider.complete(
                prompt=user_prompt,
                system=system_prompt
            )
            if rewritten.startswith('"') and rewritten.endswith('"'):
                rewritten = rewritten[1:-1]
            return rewritten
        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
            return query

    async def answer_with_citations(
        self,
        question: str,
        doc_summaries: Dict[str, str],
        chunks: List[Dict],
    ) -> str:
        evidence_blocks = []
        for c in chunks:
            header = (
                f"SOURCE chunk_id={c['chunk_id']} "
                f"doc_id={c['doc_id']} "
                f"chunk_index={c['chunk_index']} "
                f"chars={c['start_char']}-{c['end_char']} "
                f"type={c.get('chunk_type', 'unknown')}"
            )
            evidence_blocks.append(header + "\n" + c["text"])

        summaries_txt = ""
        if doc_summaries:
            parts = []
            for doc_id, summ in doc_summaries.items():
                parts.append(f"doc_id={doc_id} summary:\n{summ}")
            summaries_txt = "\n\n".join(parts)

        rules = [
            "You are a precise QA system. You MUST follow these rules:",
            "1) Use ONLY the provided SOURCES as evidence.",
            '2) If the answer is not supported by the SOURCES, say: "Not found in the document." and list the closest relevant sources.',
            "3) Every non-trivial statement must include citations in square brackets with chunk_id(s), e.g. [chunk_123].",
            "4) When citing, prefer the single best chunk; use multiple only if necessary.",
        ]
        if self.answer_only_question:
            rules.append("5) Answer ONLY what the question asks. Do not include subsequent actions or extra context unless explicitly requested.")
        else:
            rules.append("5) Keep the answer concise and directly responsive.")

        rules.append("")
        rules.append("Output format:")
        rules.append("Answer: ...")
        rules.append("Sources:")
        rules.append('- chunk_id=... doc_id=... chunk_index=... chars=... excerpt="..."')
        instructions = "\n".join(rules)

        prompt = (
            f"QUESTION:\n{question}\n\n"
            f"DOC_SUMMARIES (context only):\n{summaries_txt}\n\n"
            f"SOURCES:\n\n" + "\n\n---\n\n".join(evidence_blocks)
        )

        return await self.provider.complete(
            prompt=prompt,
            system=instructions
        )
