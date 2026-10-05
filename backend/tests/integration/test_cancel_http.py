"""HTTP boundary for authenticated run cancellation."""
from fastapi.testclient import TestClient

from jevtriage.auth.core import Principal
from jevtriage.main import create_app


def test_cancel_requires_session_and_csrf(monkeypatch):
    from jevtriage.auth import core

    principal = Principal("tenant-a", "owner", (), frozenset({"requester"}), True)
    async def session(_token):
        return principal, "csrf-ok"
    monkeypatch.setattr(core, "session_principal", session)
    app = create_app()
    app.dependency_overrides[core.get_principal] = lambda: principal
    with TestClient(app) as client:
        path = "/api/requests/request-1/runs/run-1/cancel"
        assert client.post(path).status_code == 403
        client.cookies.set("jev_session", "session")
        assert client.post(path, headers={"X-CSRF-Token": "wrong"}).status_code == 403


def test_cancel_http_maps_role_and_tenant_denials(monkeypatch):
    from jevtriage.auth import core
    from jevtriage.jobs import api as jobs_api

    principal = [Principal("tenant-b", "reader", (), frozenset({"team_member"}), True)]
    async def session(_token):
        return principal[0], "csrf-ok"
    monkeypatch.setattr(core, "session_principal", session)
    async def deny(_principal, _request_id, _run_id):
        if _principal.tenant_id != "tenant-a":
            raise LookupError("missing")
        if not ({"requester", "operator"} & _principal.roles):
            raise PermissionError("cancel requires the author or operator")
        return {"status": "cancelled"}
    monkeypatch.setattr(jobs_api, "cancel_run", deny)
    app = create_app()
    app.dependency_overrides[core.get_principal] = lambda: principal[0]
    with TestClient(app) as client:
        path = "/api/requests/request-1/runs/run-1/cancel"
        headers = {"X-CSRF-Token": "csrf-ok"}
        client.cookies.set("jev_session", "session")
        client.cookies.set("jev_csrf", "csrf-ok")
        assert client.post(path, headers=headers).status_code == 404

        principal[0] = Principal("tenant-a", "reader", (), frozenset({"team_member"}), True)
        assert client.post(path, headers=headers).status_code == 403
        principal[0] = Principal("tenant-a", "owner", (), frozenset({"requester"}), True)
        assert client.post(path, headers=headers).status_code == 200
