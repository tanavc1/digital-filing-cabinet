import sys
import os
import json
import time
from typing import List, Dict, Any

# Ensure we can import from local
sys.path.append(os.getcwd())

from main import Config, RAGEngine, DEFAULT_WORKSPACE_ID

import sys
import os
import json
import time
import asyncio
from typing import List, Dict, Any

# Ensure we can import from local
sys.path.append(os.getcwd())

from main import Config, RAGEngine, DEFAULT_WORKSPACE_ID
from docling.document_converter import DocumentConverter

# Configuration
WORKSPACE = "Accuracy"
DATA_DIR = "accuracy_benchmark_data"

TEST_CASES = [
    {
        "id": "T1",
        "file": "complex_rental_agreement.pdf",
        "query": "What is the non-refundable deposit amount?",
        "expected_phrases": ["$500", "per animal"],
        "expected_abstain": False,
        "type": "Specific (PDF)"
    },
    {
        "id": "T2",
        "file": "financial_report_Q3.docx",
        "query": "What was Q3 revenue growth?",
        "expected_phrases": ["14.5%"],
        "expected_abstain": False,
        "type": "Specific (DOCX)"
    },
    {
        "id": "T3",
        "file": "financial_report_Q3.docx",
        "query": "Why did profit margin drop?",
        "expected_phrases": ["increased R&D", "AI initiative"],
        "expected_abstain": False,
        "type": "Synthesis (DOCX)"
    },
    {
        "id": "T4",
        "file": "product_roadmap_2025.pptx",
        "query": "When is Phase 2 launching?",
        "expected_phrases": ["Q4 2025"],
        "expected_abstain": False,
        "type": "Specific (PPTX)"
    },
    {
        "id": "T5",
        "file": "product_roadmap_2025.pptx",
        "query": "What is the unit cost?",
        "expected_phrases": ["$150"],
        "expected_abstain": False,
        "type": "Low-visibility (Footnote)"
    },
    {
        "id": "T6",
        "file": "needle_history.txt",
        "query": "Where is the scepter?",
        "expected_phrases": ["Caves of Zog"],
        "expected_abstain": False,
        "type": "Needle-in-haystack (TXT)"
    },
    {
        "id": "T7",
        "file": "complex_rental_agreement.pdf",
        "query": "Who is the Emperor of Zog?",
        "expected_phrases": [],
        "expected_abstain": True,
        "type": "Negative / Hallucination Check"
    }
]

async def run_benchmark():
    print("Initializing Engine...")
    cfg = Config.from_env(db_path="./lancedb_data")
    engine = RAGEngine(cfg)
    
    # We need a dedicated converter for accuracy tests
    converter = DocumentConverter()

    print(f"\n--- Ingesting {len(set(t['file'] for t in TEST_CASES))} Files into Workspace '{WORKSPACE}' ---")
    files_to_ingest = set(t['file'] for t in TEST_CASES)
    
    start_ingest = time.time()
    for fname in files_to_ingest:
        path = os.path.abspath(os.path.join(DATA_DIR, fname))
        if not os.path.exists(path):
            print(f"ERROR: File not found: {path}")
            continue
            
        print(f"Ingesting {fname}...")
        try:
            text_content = ""
            
            if fname.endswith(".txt"):
                # Direct read for TXT
                with open(path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            else:
                # Use Docling for binaries
                # Convert takes path, returns ConversionResult
                # Then result.document.export_to_markdown()
                result = converter.convert(path)
                text_content = result.document.export_to_markdown()

            # Save temp txt for ingestion
            temp_txt = path + ".extracted.txt"
            with open(temp_txt, "w", encoding="utf-8") as f:
                f.write(text_content)
                
            # Ingest (awaitable!)
            await engine.ingest_text_file(
                temp_txt,
                title=fname,
                source=fname,
                workspace_id=WORKSPACE
            )
            
        except Exception as e:
            print(f"Failed to ingest {fname}: {e}")
            import traceback
            traceback.print_exc()

    print(f"Ingestion complete in {time.time() - start_ingest:.2f}s\n")

    print("--- Running Accuracy Tests ---\n")
    results = []
    
    for case in TEST_CASES:
        print(f"Test {case['id']} [{case['type']}]")
        print(f"Query: {case['query']}")
        
        start_q = time.time()
        # Query is now Async
        try:
            res = await engine.query(case['query'], workspace_id=WORKSPACE)
        except Exception as e:
            print(f"Query Failed: {e}")
            res = {"answer": "", "abstained": True}
            
        duration = time.time() - start_q
        
        answer = res.get("answer", "")
        abstained = res.get("abstained", False)
        
        # Validation
        passed = True
        reasons = []
        
        if case['expected_abstain']:
            if not abstained:
                passed = False
                reasons.append(f"Expected ABSTAIN, but got answer: '{answer}'")
        else:
            if abstained:
                passed = False
                reasons.append("Unexpected ABSTAIN")
            
            # Check phrases
            lower_ans = answer.lower()
            for phrase in case['expected_phrases']:
                if phrase.lower() not in lower_ans:
                    passed = False
                    reasons.append(f"Missing phrase: '{phrase}'")
        
        status = "PASS" if passed else "FAIL"
        print(f"Result: {status} ({duration:.2f}s)")
        if not passed:
            print(f"Failure Reasons: {reasons}")
            print(f"Actual Answer: {answer}")
        
        print("-" * 40)
        
        results.append({
            "id": case["id"],
            "type": case["type"],
            "status": status,
            "duration": duration,
            "reasons": reasons
        })

    # Summary
    print("\n--- Summary ---")
    passed_count = sum(1 for r in results if r['status'] == 'PASS')
    total = len(results)
    if total > 0:
        print(f"Passed: {passed_count}/{total} ({passed_count/total*100:.1f}%)")
    
    # Write report json for parsing
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
