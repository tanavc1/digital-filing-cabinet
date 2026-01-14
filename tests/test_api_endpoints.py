"""
API Endpoint Tests
==================

Tests for all major API endpoints to ensure production readiness.
"""

import pytest
from fastapi.testclient import TestClient
import os
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required env vars for testing
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "test-key")
os.environ["API_SECRET"] = "test-api-secret"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"

from api import app


class TestHealthEndpoints:
    """Test basic health and status endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data or "name" in data or "status" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_login_with_correct_password(self, client):
        """Test login with correct password returns token."""
        response = client.post(
            "/auth/login",
            json={"password": "test-admin-password"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data or "api_key" in data or "access_token" in data
    
    def test_login_with_wrong_password(self, client):
        """Test login with wrong password fails."""
        response = client.post(
            "/auth/login",
            json={"password": "wrong-password"}
        )
        assert response.status_code in [401, 403]


class TestAuditEndpoints:
    """Test audit-related endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers."""
        return {"X-API-Key": "test-api-secret"}
    
    def test_list_audit_templates(self, client, auth_headers):
        """Test listing audit templates."""
        response = client.get("/audit/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        templates = data["templates"]
        assert len(templates) >= 3  # We have at least 3 predefined templates
        
        # Verify template structure
        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "question_count" in template
    
    def test_get_specific_template(self, client, auth_headers):
        """Test getting a specific audit template."""
        response = client.get(
            "/audit/templates/commercial_lease",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "commercial_lease"
        assert "questions" in data
        assert len(data["questions"]) >= 5
    
    def test_get_nonexistent_template(self, client, auth_headers):
        """Test getting a template that doesn't exist."""
        response = client.get(
            "/audit/templates/nonexistent_template",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_run_audit_without_template(self, client, auth_headers):
        """Test running audit without template fails appropriately."""
        response = client.post(
            "/audit/run",
            json={"workspace_id": "default"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "template_id" in response.json().get("detail", "").lower() or \
               "custom_questions" in response.json().get("detail", "").lower()


class TestCompareEndpoints:
    """Test document comparison endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"X-API-Key": "test-api-secret"}
    
    def test_compare_nonexistent_documents(self, client, auth_headers):
        """Test comparing documents that don't exist."""
        response = client.post(
            "/compare",
            json={
                "doc_id_a": "nonexistent_doc_1",
                "doc_id_b": "nonexistent_doc_2",
                "workspace_id": "default"
            },
            headers=auth_headers
        )
        # Should return 404 or error about missing documents
        assert response.status_code in [404, 500, 400]


class TestDocumentEndpoints:
    """Test document management endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"X-API-Key": "test-api-secret"}
    
    def test_list_documents(self, client, auth_headers):
        """Test listing documents in a workspace."""
        response = client.get(
            "/documents?workspace_id=default",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data or isinstance(data, list)


class TestIngestEndpoints:
    """Test document ingestion endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"X-API-Key": "test-api-secret"}
    
    def test_ingest_text_file(self, client, auth_headers):
        """Test ingesting a plain text file."""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document for ingestion testing.")
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = client.post(
                    "/ingest/any",
                    files={"file": ("test.txt", f, "text/plain")},
                    data={"workspace_id": "test_ingest"},
                    headers=auth_headers
                )
            
            # Should succeed or return appropriate error
            assert response.status_code in [200, 201, 422]  # 422 for validation
        finally:
            os.unlink(temp_path)


class TestQueryEndpoints:
    """Test query/search endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"X-API-Key": "test-api-secret"}
    
    def test_query_empty_workspace(self, client, auth_headers):
        """Test querying an empty workspace."""
        response = client.post(
            "/query_stream",
            json={
                "q": "What is the salary?",
                "workspace_id": "empty_workspace_test"
            },
            headers=auth_headers
        )
        # Should return 200 with SSE stream (even if no results)
        assert response.status_code == 200


class TestSecurityMiddleware:
    """Test that security middleware is working."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_protected_endpoint_without_auth(self, client):
        """Test that protected endpoints require authentication."""
        response = client.get("/documents")
        # Should be blocked without auth
        assert response.status_code in [401, 403, 422]
    
    def test_protected_endpoint_with_wrong_key(self, client):
        """Test that wrong API key is rejected."""
        response = client.get(
            "/documents",
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code in [401, 403]


def run_tests():
    """Run all API tests."""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
