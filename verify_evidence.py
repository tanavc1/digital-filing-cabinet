
import os
import shutil
import json
import asyncio
import time
from main import Config, RAGEngine

def setup_env():
    # clean db for isolation
    db_path = "./test_lancedb_evidence"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    os.makedirs("sample_docs", exist_ok=True)
    return Config.from_env(db_path=db_path)

async def run_tests():
    cfg = setup_env()
    engine = RAGEngine(cfg)
    
    print("--- Ingesting Docs ---")
    ws_main = "Main"
    ws_iso = "Isolation"
    
    # Create sample docs
    with open("sample_docs/contract.txt", "w") as f:
        f.write("The penalty for late delivery is exactly $5,000 per day, capped at $50,000 total.")
    
    with open("sample_docs/project_alpha.txt", "w") as f:
        f.write(
            "Project Alpha Phase 1 involves initial design.\n" * 20 + 
            "The total budget for Phase 1 is $1.5M.\n" + 
            "Project Alpha Phase 2 follows immediately.\n" + 
            "The total budget for Phase 2 is $2.0M.\n" * 10
        )

    with open("sample_docs/mars_plan.pptx.txt", "w") as f:
         f.write("Mars Colonization Strategy\nMission Goals\nEstablish permanent base by 2035\nUtilize in-situ resource utilization (ISRU)\nDevelop food production systems\n\nBudget & Risks\nEstimated Cost: $500 Billion over 10 years\nPrimary Risk: Radiation exposure during transit")

    # Ingest docs (Setup)
    await engine.ingest_text_file("sample_docs/space_overview.txt", workspace_id=ws_main)
    await engine.ingest_text_file("sample_docs/project_alpha.txt", workspace_id=ws_main)
    # The new document (Mars Plan) - strictly await
    print("Ingesting Mars Plan...")
    await engine.ingest_text_file("sample_docs/mars_plan.pptx.txt", workspace_id=ws_main, title="Mars Plan")
    
    print("Ingesting Contract (Isolation)...")
    await engine.ingest_text_file("sample_docs/contract.txt", workspace_id=ws_iso) # For isolation test
    
    # Also ingest contract into Main for Test 1
    await engine.ingest_text_file("sample_docs/contract.txt", workspace_id=ws_main)
    # Ideally ingest PPTX too if we can hook it up or use existing generic ingest
    # assuming ingest_any is via API, but here we use engine.ingest_text_file or we need to extract first.
    # Since we are testing engine, we can just simulate the text content of PPTX if we don't want to depend on docling here
    # OR we can assume docling extracted text available.


    # TEST 1: Exact Quote
    q1 = "What is the penalty for late delivery?"
    start = time.time()
    res1 = await engine.query(q1, workspace_id=ws_main)
    dur = time.time() - start
    print(f"\n[TEST 1] Exact Quote (Duration: {dur:.2f}s)")
    print(f"A: {res1['answer']}")
    print(f"Sources: {json.dumps(res1['sources'], indent=2)}")
    
    if res1["abstained"]:
        print("FAIL: Abstained on known fact.")
    else:
        # Check source excerpt contains exact text
        txt = "exactly $5,000 per day"
        
        # Phase 3 Check: Real Offsets
        valid_offsets = False
        for s in res1["sources"]:
            if txt in s.get("quote", ""):
                if s["end_char"] > s["start_char"]: # Simple valid check
                    valid_offsets = True
                    print(f"OFFSET CHECK PASS: {s['start_char']} - {s['end_char']}")
                else:
                    print(f"OFFSET CHECK FAIL: Invalid offsets {s['start_char']} - {s['end_char']}")
        
        found = any(txt in s.get("quote", "") for s in res1["sources"])
        if found and valid_offsets:
            print("PASS: Found exact quote with valid offsets.")
        else:
            print(f"FAIL: Quote not found or offsets invalid. Sources: {len(res1['sources'])}")

    # TEST 2: Multi-Chunk Answer (Budget total)
    q2 = "What are the budgets for Phase 1 and Phase 2?"
    start = time.time()
    res2 = await engine.query(q2, workspace_id=ws_main)
    dur = time.time() - start
    print(f"\n[TEST 2] Multi-Chunk Answer (Duration: {dur:.2f}s)")
    for s in res2["sources"]:
        print(f"The total budget for Phase {s.get('chunk_index', '?')} is {s.get('quote', '')}")
    print(f"A: {res2['answer']}")
    
    if "$1.5M" in res2["answer"] and "$2.0M" in res2["answer"]:
        print("PASS: Retrieved facts from multiple locations.")
    else:
        print("FAIL: Missing budget figures.")

    # TEST 3: PPTX Bullet Points
    print("\n[TEST 3] PPTX Bullet Points")
    q3 = "What are the mission goals for Mars?"
    res3 = await engine.query(q3, workspace_id=ws_main)
    print(f"A: {res3['answer']}")
    
    if "permanent base" in res3["answer"] and "ISRU" in res3["answer"]:
        print("PASS: Retrieved bullet points.")
    else:
        print("FAIL: Missing bullet points.")

    # TEST 4: Negative / Abstain
    print("\n[TEST 4] Negative/Abstain")
    q4 = "Who is the CEO of Project Alpha?"
    res4 = await engine.query(q4, workspace_id=ws_main)
    print(f"A: {res4['answer']}")
    print(f"Explanation: {res4.get('explanation')}")
    
    if res4["abstained"] and res4["answer"] == "Not found in the document.":
        print("PASS: Correctly abstained.")
    else:
        print("FAIL: Did not abstain or hallucinated.")

    # TEST 5: Workspace Isolation
    print("\n[TEST 5] Workspace Isolation")
    # Query in Isolation workspace for "Mars" (should fail, only contract is there)
    q5 = "What are the mission goals?"
    res5 = await engine.query(q5, workspace_id=ws_iso)
    print(f"A: {res5['answer']}")
    
    if res5["abstained"]:
         print("PASS: Isolated workspace did not leak Mars doc.")
    else:
         print("FAIL: Leaked Mars doc info!")

def run():
    asyncio.run(run_tests())

if __name__ == "__main__":
    run()
