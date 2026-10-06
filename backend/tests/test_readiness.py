from fastapi.testclient import TestClient

from ildongi import main


class UnavailableDriver:
    async def verify_connectivity(self) -> None:
        raise OSError("connection unavailable")

    async def close(self) -> None:
        return None


def test_ready_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(main, "create_driver", lambda settings: UnavailableDriver())
    with TestClient(main.create_app()) as client:
        response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Neo4j unavailable"}
