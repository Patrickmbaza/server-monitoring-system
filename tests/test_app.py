import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_index_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert "service" in data
    assert data["service"] == "Server Monitoring System"


def test_status_endpoint(client):
    """Test status endpoint"""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.get_json()
    assert "timestamp" in data
    assert "summary" in data


def test_hosts_endpoint(client):
    """Test hosts endpoint"""
    response = client.get("/hosts")
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_time_endpoint(client):
    """Test time endpoint"""
    response = client.get("/time")
    assert response.status_code == 200
    data = response.get_json()
    assert "server_time_utc" in data
    assert "times" in data


def test_dashboard_endpoint(client):
    """Test dashboard endpoint"""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Server Monitoring Dashboard" in response.data
