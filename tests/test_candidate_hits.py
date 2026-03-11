"""
Candidate Hits Tests
===================
Tests for candidate generation logic and API updates.
"""
import pytest
from fastapi.testclient import TestClient
import os
import sys

# Setup imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playbook_engine import PlaybookEngine
from models.clause import ClauseType, ClauseExtraction, ExtractionStatus, Candidate
from api import app, _clauses

class MockEngine:
    pass

class MockProvider:
    pass

class TestCandidateLogic:
    """Tests for playbook_engine candidate generation."""
    
    def test_generate_candidates_keyword_scan(self):
        """Test that keywords are found and mapped to correct pages."""
        # Bypass full init
        pe = PlaybookEngine.__new__(PlaybookEngine)
        pe.engine = MockEngine()
        
        content = """
        ## Page 1
        Intro...
        ## Page 2
        10. ASSIGNMENT. We shall not assign.
        """
        
        candidates = pe._generate_candidates(content, ClauseType.ASSIGNMENT_CONSENT)
        
        assert len(candidates) > 0
        assert candidates[0].match_type == "keyword"
        assert candidates[0].page == 2
        assert "assign" in candidates[0].snippet.lower()


class TestCandidateAPI:
    """Tests for API handling of candidate data."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        # API requires X-API-Key if checking secrets
        return {"X-API-Key": "test-api-secret"}
        
    def test_update_clause_with_candidates(self, client, auth_headers):
        """Test resolving a clause via API by sending candidates."""
        # populate dummy clause
        clause_id = "test-clause-123"
        _clauses[clause_id] = ClauseExtraction(
            id=clause_id,
            doc_id="doc1",
            clause_type=ClauseType.ASSIGNMENT_CONSENT,
            status=ExtractionStatus.UNRESOLVED,
            extracted_value="",
            candidates=[Candidate(page=1, snippet="foo", score=0.9, match_type="keyword", locator="test")]
        )
        
        # Verify initial state via API
        resp = client.get(f"/clauses/{clause_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "candidates" in data
        assert len(data["candidates"]) == 1
        
        # Update via API (Simulate User Resolving)
        update_payload = {
            "status": "resolved",
            "extracted_value": "foo",
            "candidates": [] # clear
        }
        
        resp = client.put(f"/clauses/{clause_id}", json=update_payload, headers=auth_headers)
        assert resp.status_code == 200
        
        # Verify update
        updated_data = resp.json()
        assert updated_data["status"] == "resolved"
        assert updated_data["extracted_value"] == "foo"
        assert len(updated_data["candidates"]) == 0
