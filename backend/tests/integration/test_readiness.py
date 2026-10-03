from fastapi.testclient import TestClient

from jevtriage.main import create_app


def test_ready_with_running_neo4j() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
