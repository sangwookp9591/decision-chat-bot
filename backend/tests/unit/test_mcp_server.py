"""Dev startup restrictions, protocol metadata and web-equivalent source authorization."""

from types import SimpleNamespace

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from ildongi.auth.types import Principal
from ildongi.mcp_server import service
from ildongi.mcp_server.api import McpSettings, create_server, invoke


def settings(**values):
    return McpSettings(_env_file=None, **values)


@pytest.mark.parametrize("values", [{}, {"mcp_auth_mode": "oauth"},
    {"mcp_auth_mode": "dev", "mcp_host": "0.0.0.0"},
    {"mcp_auth_mode": "dev", "mcp_dev_user": ""}])
def test_startup_fails_closed(monkeypatch, values):
    for key in ("MCP_AUTH_MODE", "MCP_HOST", "MCP_DEV_USER"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValidationError):
        settings(**values)


async def test_tools_schemas_and_annotations():
    server = create_server(settings(mcp_auth_mode="dev", mcp_allow_submit=True))
    tools = await server.list_tools()
    assert {t.name for t in tools} == {"submit_request", "get_request_result",
                                      "list_my_requests", "list_review_queue", "list_tasks"}
    for tool in tools:
        assert tool.inputSchema and tool.outputSchema and tool.description
        assert tool.annotations.readOnlyHint == (tool.name != "submit_request")
    submit = next(t for t in tools if t.name == "submit_request")
    assert submit.inputSchema["properties"]["text"]["maxLength"] == 20_000


@pytest.mark.parametrize("owner,source_grant,expected", [(False, False, False),
                                                         (True, False, True),
                                                         (False, True, True)])
async def test_source_matches_web_scope(monkeypatch, owner, source_grant, expected):
    p = Principal("tenant", "user", ("org",), frozenset({"requester"}), source_grant)
    async def detail(*args):
        return {"request": {"tenant_id": "tenant", "created_by": "user" if owner else "other",
                            "status": "pending", "text": "private source"},
                "evidence": [{"source_text": "private source"}]}
    async def progress(*args):
        return {"final": False, "preliminary": {"description": "private source"}}
    monkeypatch.setattr(service.ingest, "visible_detail", detail)
    monkeypatch.setattr(service.judgment, "visible_progress", progress)
    data = await service.get_request_result(p, "request")
    assert ("text" in data["request"]["request"]) == expected
    assert ("description" in data["progress"]["preliminary"]) == source_grant


async def test_invisible_request_stops_before_judgment(monkeypatch):
    async def missing(*args):
        return None
    monkeypatch.setattr(service.ingest, "visible_detail", missing)
    with pytest.raises(LookupError):
        await service.get_request_result(Principal("t", "u", (), frozenset()), "foreign")


async def test_transport_never_echoes_secret_or_source(monkeypatch):
    from ildongi.mcp_server import api
    async def failed(*args):
        raise RuntimeError("SECRET_VALUE PRIVATE_SOURCE")
    monkeypatch.setattr(api, "dev_principal", failed)
    ctx = SimpleNamespace(request_context=SimpleNamespace(lifespan_context={"email": "dev"}))
    with pytest.raises(ToolError) as error:
        await invoke(ctx, failed)
    assert "SECRET_VALUE" not in str(error.value)
    assert "PRIVATE_SOURCE" not in str(error.value)


async def test_sdk_validation_does_not_echo_input():
    server = create_server(settings(mcp_auth_mode="dev", mcp_allow_submit=True))
    response = await server.call_tool("submit_request", {"text": "PRIVATE_SOURCE" * 2000})
    assert response.isError
    assert "PRIVATE_SOURCE" not in response.content[0].text
    assert "PRIVATE_SOURCE" not in str(await server.call_tool("PRIVATE_SOURCE", {}))
    assert (await server.call_tool("list_my_requests", {"limit": 11})).isError


def test_http_transport_flags_and_limits(monkeypatch):
    from starlette.testclient import TestClient

    from ildongi.mcp_server import api

    async def principal(*args):
        return Principal("t", "u", (), frozenset({"requester"}))
    monkeypatch.setattr(api, "dev_principal", principal)
    headers = {"Accept": "application/json, text/event-stream"}
    initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-03-26", "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"}}}
    listing = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    for enabled in (False, True):
        server = create_server(settings(mcp_auth_mode="dev", mcp_sse_enabled=enabled))
        with TestClient(server.streamable_http_app(), base_url="http://127.0.0.1:8787") as client:
            response = client.post("/mcp", json=initialize, headers=headers)
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            assert "mcp-session-id" not in response.headers
            response = client.post("/mcp", json=listing, headers=headers)
            assert {t["name"] for t in response.json()["result"]["tools"]} == {
                "get_request_result", "list_my_requests", "list_review_queue", "list_tasks"}
            response = client.post("/mcp/stream", json=initialize, headers=headers)
            assert response.status_code == (200 if enabled else 404)
            if enabled:
                assert response.headers["content-type"].startswith("text/event-stream")
                assert '"result"' in response.text
                stream_tools = client.post("/mcp/stream", json=listing, headers=headers)
                assert '"submit_request"' not in stream_tools.text


def test_http_rate_and_body_limits(monkeypatch):
    from starlette.testclient import TestClient

    from ildongi.mcp_server import api

    async def principal(*args):
        return Principal("t", "u", (), frozenset())
    monkeypatch.setattr(api, "dev_principal", principal)
    with TestClient(create_server(settings(mcp_auth_mode="dev")).streamable_http_app(),
                    base_url="http://127.0.0.1:8787") as client:
        response = client.post("/mcp", content=b"x" * (api.MAX_REQUEST_BYTES + 1))
        assert response.status_code == 429 and response.headers["retry-after"] == "60"
        for _ in range(59):
            assert client.post("/mcp", content=b"{}").status_code != 429
        response = client.post("/mcp", content=b"{}")
        assert response.status_code == 429 and response.headers["retry-after"] == "60"


async def test_result_and_concurrency_limits():
    import asyncio

    from ildongi.mcp_server.api import MAX_RESULT_BYTES, RequestLimits, RequestsResult, result

    with pytest.raises(ToolError):
        result(RequestsResult(summary="summary", items=[{"text": "x" * MAX_RESULT_BYTES}]))
    entered, release = asyncio.Event(), asyncio.Event()
    async def app(scope, receive, send):
        entered.set()
        await release.wait()
    limiter = RequestLimits(app)
    scope = {"type": "http", "path": "/mcp"}
    async def receive():
        return {"type": "http.request", "body": b""}
    messages = []
    async def send(message):
        messages.append(message)
    tasks = [asyncio.create_task(limiter(scope, receive, send)) for _ in range(4)]
    await entered.wait()
    await asyncio.sleep(0)
    await limiter(scope, receive, send)
    assert messages[0]["status"] == 429
    assert (b"retry-after", b"60") in messages[0]["headers"]
    release.set()
    await asyncio.gather(*tasks)
    assert limiter.active == 0
