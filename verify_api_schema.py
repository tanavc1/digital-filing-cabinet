import sys
from api import QueryResponse, ClosestMentionOut, SourceOut

def test_schema():
    print("Testing QueryResponse schema...")
    
    # Mock RAGEngine output (Abstain case)
    engine_out_abstain = {
        "answer": "Not found.",
        "abstained": True,
        "explanation": "No evidence.",
        "closest_mentions": [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "excerpt": "some text",
                "rerank_score": 0.9
            }
        ],
        "sources": []
    }
    
    # Validate instantiation
    try:
        closest = [ClosestMentionOut(**c) for c in engine_out_abstain["closest_mentions"]]
        resp = QueryResponse(
            answer=engine_out_abstain["answer"],
            abstained=engine_out_abstain["abstained"],
            sources=[],
            explanation=engine_out_abstain["explanation"],
            closest_mentions=closest
        )
        print("PASS: Instantiated QueryResponse with explanation and closest_mentions.")
        assert resp.explanation == "No evidence."
        assert len(resp.closest_mentions) == 1
        assert resp.closest_mentions[0].excerpt == "some text"
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    # Mock RAGEngine output (Found case)
    engine_out_found = {
        "answer": "The answer is 42.",
        "abstained": False,
        "sources": [
             {
                "chunk_id": "c1",
                "doc_id": "d1",
                "chunk_index": 0,
                "start_char": 0,
                "end_char": 10,
                "excerpt": "42",
                "rerank_score": 1.0
             }
        ]
    }

    try:
        sources = [SourceOut(**s) for s in engine_out_found["sources"]]
        resp = QueryResponse(
            answer=engine_out_found["answer"],
            abstained=engine_out_found["abstained"],
            sources=sources,
            # explanation/closest_mentions optional/default
        )
        print("PASS: Instantiated QueryResponse for found case.")
        assert resp.explanation is None
        assert resp.closest_mentions == []
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)
        
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_schema()
