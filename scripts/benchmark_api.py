import urllib.request
import json
import time
import sys

BASE_URL = "http://localhost:8000"
WORKSPACE = "Main"

QUERIES = [
    "What is the penalty for late delivery?",
    "What are the mission goals?",
    "Who is the CEO of Project Alpha?"
]

def run_benchmark():
    print(f"Benchmarking RAG Speed against {BASE_URL}...\n")
    
    total_time = 0
    count = 0

    for q in QUERIES:
        print(f"Query: '{q}'")
        payload = json.dumps({
            "q": q,
            "workspace_id": WORKSPACE
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{BASE_URL}/query",
            data=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        start = time.time()
        try:
            with urllib.request.urlopen(req) as f:
                res_body = f.read().decode('utf-8')
                data = json.loads(res_body)
                
            duration = time.time() - start
            total_time += duration
            count += 1
            
            ans = data.get("answer", "")
            # Check for verification (evidence list populated)
            evidence = data.get("evidence", [])
            verified = "Verified (Green)" if evidence else "Abstained (Red)"
            
            print(f"  -> Time: {duration:.2f}s")
            print(f"  -> Result: {verified}")
            print(f"  -> Answer: {ans[:60]}..." if len(ans) > 60 else f"  -> Answer: {ans}")
            
        except Exception as e:
            print(f"  -> Error: {e}")
        print("-" * 30)
        
    if count > 0:
        print(f"\nAverage Time: {total_time / count:.2f}s")

if __name__ == "__main__":
    run_benchmark()
