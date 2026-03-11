"""
Hallucination Detection Test Suite
===================================

Tests to ensure the RAG system does NOT hallucinate answers.
These tests verify that:
1. When information is not in docs, the system abstains
2. Quotes are actually present in the source documents
3. Citations are accurate and verifiable
"""

import pytest
import asyncio
import os
import sys
import shutil
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables
os.environ.setdefault("OFFLINE_MODE", "true")
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("OLLAMA_MODEL", "phi4-mini")

from core import RAGEngine, Config, EvidenceContract


def write_temp_file(content: str, suffix: str = ".txt") -> str:
    """Write content to a temporary file and return the path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path


class TestHallucinationPrevention:
    """Tests to verify the system does not fabricate information."""
    
    @pytest.fixture
    def engine(self):
        """Create a test engine instance."""
        db_path = "./test_lancedb_hallucination"
        # Clean up previous test run
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        cfg = Config.from_env(db_path=db_path)
        engine = RAGEngine(cfg)
        yield engine
        # Cleanup after test
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
    
    @pytest.mark.asyncio
    async def test_abstains_when_no_relevant_docs(self, engine):
        """
        Test: If a question has no relevant documents, the system should abstain.
        The system should NOT make up an answer.
        """
        # Query about something that can't possibly be in the docs
        question = "What is the CEO's favorite color mentioned in the employment agreement?"
        
        # Run query (expecting abstention or "not found" response)
        result = await engine.query(
            question,
            workspace_id="test_workspace"
        )
        
        # Verify abstention or clear "not found" message
        assert result.get("abstained", True) or "not found" in result.get("answer", "").lower(), \
            f"System should abstain when no evidence exists. Got: {result.get('answer')}"
    
    @pytest.mark.asyncio
    async def test_quotes_exist_in_source(self, engine):
        """
        Test: Any quote returned must actually exist in the source document.
        This prevents fabricated quotes.
        """
        # First, ingest a test document with known content
        test_content = """
        EMPLOYMENT AGREEMENT
        
        This Employment Agreement is entered into as of January 1, 2024.
        
        1. COMPENSATION
        Employee shall receive a base salary of $150,000 per year.
        
        2. TERM
        The initial term of employment shall be two (2) years.
        
        3. TERMINATION
        Either party may terminate this agreement with 30 days written notice.
        """
        
        # Write to temp file and ingest
        temp_path = write_temp_file(test_content)
        try:
            await engine.ingest_text_file(
                path=temp_path,
                title="Test Employment Agreement",
                workspace_id="test_workspace"
            )
            
            # Query for information that IS in the doc
            question = "What is the base salary in the employment agreement?"
            result = await engine.query(question, workspace_id="test_workspace")
            
            # Verify sources exist and quotes are from the actual document
            sources = result.get("sources", [])
            for source in sources:
                quote = source.get("quote", "") or source.get("excerpt", "")
                if quote:
                    # The quote should be findable in our test content
                    assert quote.strip() in test_content or test_content.find(quote[:50]) >= 0, \
                        f"Quote not found in source document: {quote[:100]}"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_does_not_answer_unrelated_questions(self, engine):
        """
        Test: System should not answer questions about topics not in the documents.
        """
        # Ingest a document about employment
        test_content = """
        LEASE AGREEMENT
        
        This lease is for the property at 123 Main Street.
        Monthly rent is $5,000 due on the 1st of each month.
        The lease term is 12 months.
        """
        
        temp_path = write_temp_file(test_content)
        try:
            await engine.ingest_text_file(
                path=temp_path,
                title="Test Lease Agreement",
                workspace_id="test_workspace_2"
            )
            
            # Ask about something NOT in the document
            question = "What is the employee's health insurance deductible?"
            result = await engine.query(question, workspace_id="test_workspace_2")
            
            # Should abstain or indicate not found
            answer = result.get("answer", "").lower()
            assert result.get("abstained", False) or \
                   "not found" in answer or \
                   "no information" in answer or \
                   "cannot find" in answer or \
                   "not mentioned" in answer, \
                f"System should indicate info not found. Got: {result.get('answer')}"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_evidence_verification_rejects_fake_quotes(self, engine):
        """
        Test: The evidence verification system should reject quotes not in documents.
        """
        # Test the _verify_evidence_match method directly
        fake_evidence = {
            "quote": "This is a completely fabricated quote that doesn't exist",
            "doc_id": "nonexistent_doc",
            "chunk_id": "fake_chunk"
        }
        
        # Empty windows (no actual document content)
        empty_windows = []
        
        # Verification should fail
        result = engine._verify_evidence_match(fake_evidence, empty_windows)
        
        assert result is None, \
            "Fake evidence should be rejected by verification"


class TestAnswerAccuracy:
    """Tests to verify answer accuracy against known documents."""
    
    @pytest.fixture
    def engine(self):
        db_path = "./test_lancedb_accuracy"
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        cfg = Config.from_env(db_path=db_path)
        engine = RAGEngine(cfg)
        yield engine
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
    
    @pytest.mark.asyncio
    async def test_extracts_correct_salary(self, engine):
        """Test: System correctly extracts numerical values."""
        content = """
        EXECUTIVE EMPLOYMENT AGREEMENT
        
        Section 3. Compensation
        
        3.1 Base Salary. The Company shall pay Executive a base salary 
        of Two Hundred Fifty Thousand Dollars ($250,000) per annum.
        
        3.2 Bonus. Executive shall be eligible for an annual bonus 
        of up to 50% of base salary.
        """
        
        temp_path = write_temp_file(content)
        try:
            await engine.ingest_text_file(
                path=temp_path,
                title="Executive Agreement",
                workspace_id="test_accuracy"
            )
            
            result = await engine.query(
                "What is the executive's base salary?",
                workspace_id="test_accuracy"
            )
            
            answer = result.get("answer", "").lower()
            assert "250,000" in answer or "250000" in answer or "two hundred fifty thousand" in answer, \
                f"Should correctly extract salary. Got: {answer}"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_extracts_correct_dates(self, engine):
        """Test: System correctly extracts dates."""
        content = """
        COMMERCIAL LEASE
        
        1. TERM
        The lease term shall commence on March 1, 2024 and expire 
        on February 28, 2027, for a total term of three (3) years.
        """
        
        temp_path = write_temp_file(content)
        try:
            await engine.ingest_text_file(
                path=temp_path,
                title="Commercial Lease",
                workspace_id="test_dates"
            )
            
            result = await engine.query(
                "When does the lease term expire?",
                workspace_id="test_dates"
            )
            
            answer = result.get("answer", "").lower()
            assert "february" in answer and "2027" in answer, \
                f"Should correctly extract expiration date. Got: {answer}"
        finally:
            os.unlink(temp_path)


class TestLegalSpecificCases:
    """Tests specific to legal document analysis."""
    
    @pytest.fixture
    def engine(self):
        db_path = "./test_lancedb_legal"
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        cfg = Config.from_env(db_path=db_path)
        engine = RAGEngine(cfg)
        yield engine
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
    
    @pytest.mark.asyncio
    async def test_identifies_change_of_control(self, engine):
        """Test: System correctly identifies change of control clauses."""
        content = """
        ASSET PURCHASE AGREEMENT
        
        Section 8. Change of Control
        
        8.1 Definition. "Change of Control" means (a) a merger or consolidation 
        of the Company with another entity, (b) the sale of all or substantially 
        all of the Company's assets, or (c) the acquisition of more than 50% 
        of the Company's voting securities by any person or group.
        
        8.2 Effect. Upon a Change of Control, the Purchaser shall have the 
        option to terminate this Agreement with 60 days notice.
        """
        
        temp_path = write_temp_file(content)
        try:
            await engine.ingest_text_file(
                path=temp_path,
                title="Asset Purchase Agreement",
                workspace_id="test_legal"
            )
            
            result = await engine.query(
                "Is there a change of control clause and what triggers it?",
                workspace_id="test_legal"
            )
            
            answer = result.get("answer", "").lower()
            # Should mention key triggers
            assert "merger" in answer or "50%" in answer or "sale" in answer, \
                f"Should identify change of control triggers. Got: {answer}"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_identifies_termination_provisions(self, engine):
        """Test: System correctly identifies termination provisions."""
        content = """
        SERVICE AGREEMENT
        
        10. TERMINATION
        
        10.1 Termination for Convenience. Either party may terminate 
        this Agreement for any reason upon ninety (90) days prior 
        written notice to the other party.
        
        10.2 Termination for Cause. Either party may terminate this 
        Agreement immediately upon written notice if the other party 
        materially breaches this Agreement and fails to cure such 
        breach within thirty (30) days.
        
        10.3 Termination Fee. If Client terminates for convenience, 
        Client shall pay Provider a termination fee equal to three 
        months of the then-current monthly fee.
        """
        
        temp_path = write_temp_file(content)
        try:
            await engine.ingest_text_file(
                path=temp_path,
                title="Service Agreement",
                workspace_id="test_legal_2"
            )
            
            result = await engine.query(
                "What are the termination provisions and any associated fees?",
                workspace_id="test_legal_2"
            )
            
            answer = result.get("answer", "").lower()
            # Should mention key details
            assert "90 days" in answer or "ninety" in answer, \
                f"Should identify notice period. Got: {answer}"
            assert "three months" in answer or "termination fee" in answer, \
                f"Should identify termination fee. Got: {answer}"
        finally:
            os.unlink(temp_path)


def run_tests():
    """Run all hallucination tests."""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
