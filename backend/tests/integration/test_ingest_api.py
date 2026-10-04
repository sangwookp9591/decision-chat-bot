from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from jevtriage.auth.core import Principal, create_session, get_principal, session_principal
from jevtriage.db.driver import get_driver
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.ingest.store import create_request, get_request_meta, request_detail, resolve_files
from jevtriage.main import create_app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def ingest_tenant():
    tenant = f"t06_{uuid4().hex}"
    await apply_schema()
    yield tenant
    driver = await get_driver()
    async with driver.session() as session:
        await (
            await session.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)
        ).consume()


async def test_text_ingest_persists_revision_run_and_job(ingest_tenant):
    result = await create_request(
        ingest_tenant,
        "user-1",
        "Need a report",
        [],
        "key-a",
        "hash-a",
        datetime.now(UTC).isoformat(),
    )
    assert result["revision"] == 1
    assert result["status"] == "judgment_pending"
    meta = await get_request_meta(ingest_tenant, result["request_id"])
    assert meta["first_received_at"] is not None
    assert meta["active_run_id"] is not None

    async def counts(tx):
        record = await (
            await tx.run(
                "MATCH (run:Run {request_id:$id,tenant_id:$tenant}) "
                "MATCH (job:Job {run_id:run.id,tenant_id:$tenant}) RETURN count(run) AS runs,count(job) AS jobs",
                id=result["request_id"],
                tenant=ingest_tenant,
            )
        ).single(strict=True)
        return record["runs"], record["jobs"]

    assert await read_tx(ingest_tenant, counts) == (1, 1)
    assert len((await request_detail(ingest_tenant, result["request_id"]))["revisions"]) == 1


async def test_http_rejects_attachment_count_and_total_bytes(ingest_tenant, tmp_path, monkeypatch):
    from types import SimpleNamespace

    import jevtriage.ingest.service as ingest_service
    monkeypatch.setattr(ingest_service, "get_settings", lambda: SimpleNamespace(data_dir=tmp_path))
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(
        ingest_tenant, "user", (), frozenset({"requester"}), True)
    with TestClient(app) as client:
        six = [("files", (f"{i}.md", b"x", "text/markdown")) for i in range(6)]
        response = client.post("/api/requests", data={"text": ""}, files=six,
                               headers={"Idempotency-Key": "six-files"})
        assert response.status_code == 400
        assert response.json()["detail"] == "too_many_attachments"
        payload = b"x" * (9 * 1024 * 1024)
        over_limit = [("files", (f"{i}.md", payload, "text/markdown")) for i in range(3)]
        response = client.post("/api/requests", data={"text": ""}, files=over_limit,
                               headers={"Idempotency-Key": "over-total"})
        assert response.status_code == 400
        assert response.json()["detail"] == "too_many_bytes"


async def test_same_idempotency_key_returns_same_request(ingest_tenant):
    args = (
        ingest_tenant,
        "user-1",
        "same payload",
        [],
        "key-b",
        "hash-b",
        datetime.now(UTC).isoformat(),
    )
    first = await create_request(*args)
    second = await create_request(*args)
    assert second == first

    async def count(tx):
        record = await (
            await tx.run(
                "MATCH (r:Request {tenant_id:$tenant}) RETURN count(r) AS n", tenant=ingest_tenant
            )
        ).single(strict=True)
        return record["n"]

    assert await read_tx(ingest_tenant, count) == 1


async def test_rejected_file_waits_until_excluded_revision(ingest_tenant):
    attachments = [
        {"id": "att_good", "filename": "good.md", "sha256": "a", "status": "ok", "units": []},
        {
            "id": "att_bad",
            "filename": "bad.pdf",
            "sha256": "b",
            "status": "rejected",
            "reason": "corrupted",
            "units": [],
        },
    ]
    first = await create_request(
        ingest_tenant,
        "user-1",
        "Please assess",
        attachments,
        "key-c",
        "hash-c",
        datetime.now(UTC).isoformat(),
    )
    assert first["status"] == "needs_file_decision"

    async def count(tx):
        row = await (
            await tx.run(
                "MATCH (j:Job {tenant_id:$tenant}) RETURN count(j) AS n", tenant=ingest_tenant
            )
        ).single(strict=True)
        return row["n"]

    assert await read_tx(ingest_tenant, count) == 0
    second = await resolve_files(
        ingest_tenant,
        first["request_id"],
        "user-1",
        1,
        ["att_bad"],
        "decision-key",
        "decision-hash",
    )
    assert second == {
        "request_id": first["request_id"],
        "revision": 2,
        "status": "judgment_pending",
    }
    assert await read_tx(ingest_tenant, count) == 1


async def test_revision_conflict_is_rejected(ingest_tenant):
    first = await create_request(
        ingest_tenant, "user-1", "text", [], "key-d", "hash-d", datetime.now(UTC).isoformat()
    )
    with pytest.raises(ValueError, match="stale_revision"):
        await resolve_files(ingest_tenant, first["request_id"], "user-1", 0, [], "key-e", "hash-e")


async def _http_client(tenant: str, role: str, *, can_read_source: bool = False):
    """Create real persisted auth/session records for router-path tests."""
    user_id, org_id = f"http_{role}_{uuid4().hex}", f"org_{uuid4().hex}"
    driver = await get_driver()
    async with driver.session() as session:
        await (await session.run(
            "MERGE (t:Tenant {id:$tenant,tenant_id:$tenant}) "
            "MERGE (o:Org {id:$org,tenant_id:$tenant}) MERGE (t)-[:HAS_ORG]->(o) "
            "CREATE (u:User {id:$user,tenant_id:$tenant,email:$email,disabled:false,"
            "can_read_source:$source}) CREATE (u)-[:MEMBER_OF {role:$role}]->(o)",
            tenant=tenant, org=org_id, user=user_id, email=f"{user_id}@test.invalid",
            source=can_read_source, role=role,
        )).consume()
    token = await create_session(tenant, user_id)
    resolved = await session_principal(token)
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    client.cookies.set("jev_session", token)
    client.cookies.set("jev_csrf", resolved[1])
    client.headers["X-CSRF-Token"] = resolved[1]
    return client, user_id


async def test_http_csrf_role_tenant_scope_and_source_gate(ingest_tenant):
    client, _ = await _http_client(ingest_tenant, "requester")
    other, _ = await _http_client(f"other_{uuid4().hex}", "operator")
    no_role, _ = await _http_client(ingest_tenant, "policy_editor")
    try:
        missing_csrf = await client.post("/api/requests", data={"text": "hello"}, headers={"X-CSRF-Token": "bad", "Idempotency-Key": "csrf"})
        assert missing_csrf.status_code == 403
        denied = await no_role.post("/api/requests", data={"text": "hello"}, headers={"Idempotency-Key": "role"})
        assert denied.status_code == 403
        accepted = await client.post("/api/requests", data={"text": "plain text intake"}, headers={"Idempotency-Key": "scope"})
        assert accepted.status_code == 202
        request_id = accepted.json()["request_id"]
        async def run_job_count(tx):
            row = await (await tx.run(
                "MATCH (run:Run {request_id:$id,tenant_id:$tenant}) "
                "MATCH (job:Job {run_id:run.id,tenant_id:$tenant}) RETURN count(job) AS n",
                id=request_id, tenant=ingest_tenant,
            )).single(strict=True)
            return row["n"]
        assert await read_tx(ingest_tenant, run_job_count) == 1
        assert (await other.get(f"/api/requests/{request_id}")).status_code == 404
        assert request_id not in str((await other.get("/api/requests")).json())
        source = await client.post("/api/requests", data={"text": "source text"}, files=[("files", ("source.md", b"line one\nline two", "text/markdown"))], headers={"Idempotency-Key": "source"})
        assert source.status_code == 202
        source_id = source.json()["request_id"]
        async def evidence(tx):
            row = await (await tx.run("MATCH (e:EvidenceSpan {request_id:$id,tenant_id:$tenant}) RETURN e.id AS id LIMIT 1", id=source_id, tenant=ingest_tenant)).single()
            return row["id"] if row else None
        span = await read_tx(ingest_tenant, evidence)
        assert span is not None
        operator, _ = await _http_client(ingest_tenant, "operator")
        try:
            assert (await operator.get(f"/api/requests/{source_id}/evidence/{span}")).status_code == 404
        finally:
            await operator.aclose()
    finally:
        await client.aclose()
        await other.aclose()
        await no_role.aclose()


async def test_http_idempotency_payload_conflict_and_stale_revision(ingest_tenant):
    client, _ = await _http_client(ingest_tenant, "requester")
    try:
        headers = {"Idempotency-Key": "same"}
        first = await client.post("/api/requests", data={"text": "first"}, headers=headers)
        retry = await client.post("/api/requests", data={"text": "first"}, headers=headers)
        conflict = await client.post("/api/requests", data={"text": "different"}, headers=headers)
        assert first.status_code == retry.status_code == 202
        assert first.json()["request_id"] == retry.json()["request_id"]
        assert conflict.status_code == 409
        stale = await client.post(f"/api/requests/{first.json()['request_id']}/revisions", data={"expected_revision": 0, "text": "late"}, headers={"Idempotency-Key": "stale"})
        assert stale.status_code == 409
    finally:
        await client.aclose()


async def test_reanalyze_creates_idempotent_run_and_preserves_assignment_counts(ingest_tenant):
    client, user_id = await _http_client(ingest_tenant, "requester")
    try:
        created = await create_request(ingest_tenant, user_id, "다시 판단할 요청입니다.", [],
                                       str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
        request_id = created["request_id"]
        from jevtriage.jobs.worker import Worker
        from jevtriage.judgment.jev_client import JevClient
        from jevtriage.judgment.service import execute_judgment
        async def run_judgment(run_id):
            async def job(tx):
                return (await (await tx.run(
                    "MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                    tenant=ingest_tenant, run=run_id,
                )).single(strict=True))["id"]
            async def handler(ctx):
                await execute_judgment(ctx, JevClient("", mode="mock"))
            await Worker(handlers={"judgment": handler}).process_job(
                ingest_tenant, await read_tx(ingest_tenant, job)
            )
        original_run = (await get_request_meta(ingest_tenant, request_id))["active_run_id"]
        await run_judgment(original_run)
        async def original_records(tx):
            row = await (await tx.run(
                "MATCH (j:Judgment {tenant_id:$tenant,request_id:$request,run_id:$run}) "
                "MATCH (v:Review {tenant_id:$tenant,request_id:$request,run_id:$run}) "
                "RETURN j.id AS judgment_id,v.id AS review_id",
                tenant=ingest_tenant, request=request_id, run=original_run,
            )).single(strict=True)
            return dict(row)
        preserved = await read_tx(ingest_tenant, original_records)
        async def seed_assignment(tx):
            await (await tx.run(
                "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
                "CREATE (a:Assignment {id:$assignment,tenant_id:$tenant,request_id:$request,"
                "run_id:q.active_run_id,pathway:'review',status:'active',created_at:datetime()}) "
                "CREATE (t:Task {id:$task,tenant_id:$tenant,request_id:$request,"
                "assignment_id:$assignment,run_id:q.active_run_id,draft_task_id:'draft-1',"
                "draft_version:1,title:'기존 업무',method:'일반 기술',lead_org:'IT팀',"
                "collab_orgs:'[]',deliverable:'결과',predecessors:'[]',status:'대기',created_at:datetime()}) "
                "CREATE (q)-[:HAS_TASK]->(t) CREATE (a)-[:HAS_TASK]->(t) "
                "SET q.assignment_id=$assignment,q.status='배정 완료'",
                tenant=ingest_tenant, request=request_id, assignment=f"as_{uuid4().hex}",
                task=f"task_{uuid4().hex}",
            )).consume()
        await write_tx(ingest_tenant, seed_assignment)
        headers = {"Idempotency-Key": "reanalyze-key"}
        payload = {"expected_revision": 1, "reason": "최신 결과 비교"}
        csrf_token = client.headers.pop("X-CSRF-Token")
        csrf_denied = await client.post(f"/api/requests/{request_id}/reanalyze", json=payload,
                                        headers=headers)
        client.headers["X-CSRF-Token"] = csrf_token
        assert csrf_denied.status_code == 403
        first = await client.post(f"/api/requests/{request_id}/reanalyze", json=payload, headers=headers)
        retry = await client.post(f"/api/requests/{request_id}/reanalyze", json=payload, headers=headers)
        assert first.status_code == retry.status_code == 202
        assert first.json()["run_id"] == retry.json()["run_id"]
        conflict = await client.post(f"/api/requests/{request_id}/reanalyze",
                                     json={**payload, "reason": "다른 사유"}, headers=headers)
        assert conflict.status_code == 409
        await run_judgment(first.json()["run_id"])

        async def counts(tx):
            row = await (await tx.run(
                "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
                "OPTIONAL MATCH (r:Run {tenant_id:$tenant,request_id:$request}) "
                "OPTIONAL MATCH (j:Job {tenant_id:$tenant,run_id:r.id}) "
                "OPTIONAL MATCH (a:Assignment {tenant_id:$tenant,request_id:$request}) "
                "OPTIONAL MATCH (t:Task {tenant_id:$tenant,request_id:$request}) "
                "RETURN q.active_run_id AS active,count(DISTINCT r) AS runs,"
                "count(DISTINCT j) AS jobs,count(DISTINCT a) AS assignments,count(DISTINCT t) AS tasks",
                tenant=ingest_tenant, request=request_id,
            )).single(strict=True)
            return dict(row)
        result = await read_tx(ingest_tenant, counts)
        assert result == {"active": first.json()["run_id"], "runs": 2, "jobs": 2,
                         "assignments": 1, "tasks": 1}
        async def preserved_records(tx):
            row = await (await tx.run(
                "MATCH (j:Judgment {tenant_id:$tenant,id:$judgment}) "
                "MATCH (v:Review {tenant_id:$tenant,id:$review}) "
                "RETURN j.id AS judgment_id,v.id AS review_id",
                tenant=ingest_tenant, judgment=preserved["judgment_id"],
                review=preserved["review_id"],
            )).single(strict=True)
            return dict(row)
        assert await read_tx(ingest_tenant, preserved_records) == preserved
        assert (await client.post(f"/api/requests/{request_id}/reanalyze",
                                  json={"expected_revision": 0},
                                  headers={"Idempotency-Key": "stale-reanalysis"})).status_code == 409
    finally:
        await client.aclose()


async def test_http_multipart_file_decision_creates_supported_revision_and_job(ingest_tenant):
    import io

    from docx import Document
    from reportlab.pdfgen import canvas
    pdf_stream = io.BytesIO()
    pdf = canvas.Canvas(pdf_stream)
    pdf.drawString(40, 750, "PDF source unit")
    pdf.save()
    pdf_content = pdf_stream.getvalue()
    doc = Document()
    doc.add_paragraph("DOCX source unit")
    doc_stream = io.BytesIO()
    doc.save(doc_stream)
    client, _ = await _http_client(ingest_tenant, "requester")
    try:
        files = [
            ("files", ("a.pdf", pdf_content, "application/pdf")),
            ("files", ("b.docx", doc_stream.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("files", ("c.md", b"# Markdown\nbody", "text/markdown")),
            ("files", ("broken.pdf", b"not a pdf", "application/pdf")),
        ]
        response = await client.post("/api/requests", data={"text": "documents"}, files=files, headers={"Idempotency-Key": "multi"})
        assert response.status_code == 202
        value = response.json()
        assert value["status"] == "needs_file_decision"
        async def inspect(tx):
            rec = await (await tx.run(
                "MATCH (r:Request {id:$id,tenant_id:$tenant})-[:HAS_REVISION]->(i:InputRevision) "
                "OPTIONAL MATCH (i)-[:HAS_ATTACHMENT]->(a:Attachment) "
                "OPTIONAL MATCH (i)-[:HAS_EVIDENCE]->(e:EvidenceSpan) "
                "OPTIONAL MATCH (j:Job {tenant_id:$tenant}) WHERE j.input_revision_id=i.id "
                "RETURN count(DISTINCT i) AS revisions,count(DISTINCT a) AS attachments,"
                "count(DISTINCT e) AS spans,count(DISTINCT j) AS jobs,"
                "collect(DISTINCT a) AS files",
                id=value["request_id"], tenant=ingest_tenant,
            )).single(strict=True)
            return rec
        stored = await read_tx(ingest_tenant, inspect)
        assert stored["revisions"] == 1 and stored["attachments"] == 4 and stored["spans"] >= 1 and stored["jobs"] == 0
        assert [dict(a) for a in stored["files"] if a], "attachment metadata missing"
        rejected = next(a for a in stored["files"] if a and a["status"] == "rejected")
        decision = await client.post(f"/api/requests/{value['request_id']}/file-decision", json={"exclude": [rejected["id"]], "expected_revision": 1}, headers={"Idempotency-Key": "exclude"})
        assert decision.status_code == 202, decision.text
        assert decision.json()["revision"] == 2 and decision.json()["status"] == "judgment_pending"
        async def jobs(tx):
            row = await (await tx.run("MATCH (j:Job {tenant_id:$tenant}) RETURN count(j) AS n", tenant=ingest_tenant)).single(strict=True)
            return row["n"]
        assert await read_tx(ingest_tenant, jobs) == 1
    finally:
        await client.aclose()


async def test_http_db_failure_returns_503_and_journals_attempt(ingest_tenant, monkeypatch, tmp_path):
    from neo4j.exceptions import ServiceUnavailable

    from jevtriage.config import get_settings
    from jevtriage.ingest import service
    from jevtriage.journal import writer
    client, _ = await _http_client(ingest_tenant, "requester")
    original = get_settings()
    monkeypatch.setattr("jevtriage.config.get_settings", lambda: original.model_copy(update={"data_dir": tmp_path}))
    monkeypatch.setattr(writer, "get_settings", lambda: original.model_copy(update={"data_dir": tmp_path}))
    async def fail(*args, **kwargs):
        raise ServiceUnavailable("injected write failure")
    monkeypatch.setattr(service, "create_request", fail)
    try:
        response = await client.post("/api/requests", data={"text": "valid"}, headers={"Idempotency-Key": "dbfail"})
        assert response.status_code == 503
        writer.flush_all()
        records = [__import__("json").loads(line) for line in (tmp_path / "journal" / "current.jsonl").read_text().splitlines()]
        received = next(record for record in records if record["kind"] == "request_received")
        failed = next(record for record in records if record["kind"] == "request_failed")
        assert received["attempt_id"] == failed["attempt_id"]
        assert failed["error_class"] == "database_unavailable" and failed["duration_ms"] >= 0
    finally:
        await client.aclose()


async def test_slo_first_received_and_supported_revision_are_immutable_after_revision(ingest_tenant):
    first = await create_request(ingest_tenant, "user", "initial", [], "slo-1", "slo-1", "2026-01-01T00:00:00+00:00")
    before = await get_request_meta(ingest_tenant, first["request_id"])
    from jevtriage.ingest.store import add_revision
    await add_revision(ingest_tenant, first["request_id"], "user", 1, "supplement", [], "slo-2", "slo-2")
    after = await get_request_meta(ingest_tenant, first["request_id"])
    assert after["first_received_at"] == before["first_received_at"]
    assert after["first_supported_revision"] == before["first_supported_revision"]
