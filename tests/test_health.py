import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_health_endpoint():
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "timestamp" in data

def test_root_docs():
    """API ドキュメントが利用可能かテスト"""
    response = client.get("/docs")
    assert response.status_code == 200
