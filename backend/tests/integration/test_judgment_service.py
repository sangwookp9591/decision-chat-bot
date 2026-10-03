"""Actual Neo4j judgment commit through one worker attempt."""
import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio

from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.ingest.store import create_request, get_request_meta
from jevtriage.jobs.worker import Worker
from jevtriage.judgment.jev_client import JevClient
from jevtriage.judgment.service import execute_judgment
from jevtriage.judgment.store import get_judgment

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    value = f"t09_{uuid4().hex}"
    await apply_schema()
    yield value
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()
    await write_tx(value, cleanup)


async def test_mock_worker_persists_information_gap_and_review(tenant):
    created = await create_request(tenant, "tester", "업무 요청이 있습니다.", [],
                                   "t09-key", "t09-hash", datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    meta = await get_request_meta(tenant, request_id)
    run_id = meta["active_run_id"]
    async def get_job(tx):
        row = await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                   tenant=tenant, run=run_id)).single(strict=True)
        return row["id"]
    job_id = await read_tx(tenant, get_job)
    async def handler(ctx):
        await execute_judgment(ctx, JevClient("", mode="mock"))
    await Worker(handlers={"judgment": handler}).process_job(tenant, job_id)
    saved = await get_judgment(tenant, request_id, run_id)
    assert saved is not None
    assert saved["judgment"]["mode"] == "mock"
    assert saved["judgment"]["feasibility"] == "정보 부족"
    assert saved["review"]["status"] == "pending"
    assert any("개발 가능성" in r for r in json.loads(saved["review"]["reasons"]))
    assert len(saved["outputs"]) >= 4
    meta = await get_request_meta(tenant, request_id)
    assert meta["status"] == "검토 대기"
    async def run_state(tx):
        return await (await tx.run("MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                                   "RETURN r.status AS status,r.first_judgment_committed_at AS first",
                                   tenant=tenant, run=run_id)).single(strict=True)
    state = await read_tx(tenant, run_state)
    assert state["status"] == "judgment_saved" and state["first"] is not None


@pytest.mark.parametrize("error_type", ["JevAuthError", "JevSchemaError", "JevRateLimited"])
async def test_jev_failure_marks_run_and_request_failed(tenant, error_type):
    from jevtriage.judgment import jev_client
    created = await create_request(tenant, "tester", "자료를 처리해 주세요.", [],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    meta = await get_request_meta(tenant, request_id)
    run_id = meta["active_run_id"]
    async def get_job(tx):
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                    tenant=tenant, run=run_id)).single(strict=True))["id"]
    job_id = await read_tx(tenant, get_job)
    class ErrorClient:
        def ask(self, *_):
            raise getattr(jev_client, error_type)(error_type)
    async def handler(ctx):
        await execute_judgment(ctx, ErrorClient())
    await Worker(handlers={"judgment": handler}).process_job(tenant, job_id)
    assert (await get_request_meta(tenant, request_id))["status"] == "실패"
    assert await get_judgment(tenant, request_id, run_id) is None
    async def run_error(tx):
        return await (await tx.run("MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                                   "RETURN r.status AS status,r.error_class AS error_class",
                                   tenant=tenant, run=run_id)).single(strict=True)
    state = await read_tx(tenant, run_error)
    assert state["status"] == "failed" and state["error_class"] == error_type


async def test_fixed_policy_survives_new_active_version(tenant):
    from jevtriage.policy.service import DEFAULT_CONFIG
    old = {**DEFAULT_CONFIG, "risk_clear_max": 0.1}
    new = {**DEFAULT_CONFIG, "risk_clear_max": 0.2}
    async def policies(tx):
        for version, config, status in ((1, old, "inactive"), (2, new, "active")):
            await (await tx.run("CREATE (:ConfigVersion {id:$id,tenant_id:$tenant,version:$version,"
                                "status:$status,config_json:$config,diff_json:'{}',"
                                "created_by:'test',reason:'version test',created_at:datetime()})",
                                id=f"cfg_{uuid4().hex}", tenant=tenant, version=version,
                                status=status, config=json.dumps(config))).consume()
    await write_tx(tenant, policies)
    created = await create_request(tenant, "tester", "업무 요청입니다.", [],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    run_id = (await get_request_meta(tenant, request_id))["active_run_id"]
    async def fix_and_job(tx):
        await (await tx.run("MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                            "SET r.versions_json=$versions", tenant=tenant, run=run_id,
                            versions=json.dumps({"config": 1, "policy": 1}))).consume()
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                    tenant=tenant, run=run_id)).single(strict=True))["id"]
    job_id = await write_tx(tenant, fix_and_job)
    async def handler(ctx):
        await execute_judgment(ctx, JevClient("", mode="mock"))
    await Worker(handlers={"judgment": handler}).process_job(tenant, job_id)
    saved = await get_judgment(tenant, request_id, run_id)
    assert json.loads(saved["judgment"]["versions"])["config_version"] == 1


async def test_reanalysis_preserves_previous_judgment(tenant):
    from jevtriage.ingest.store import add_revision
    created = await create_request(tenant, "tester", "첫 번째 요청입니다.", [],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    async def run_active():
        meta = await get_request_meta(tenant, request_id)
        run_id = meta["active_run_id"]
        async def job(tx):
            return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                        tenant=tenant, run=run_id)).single(strict=True))["id"]
        async def handler(ctx):
            await execute_judgment(ctx, JevClient("", mode="mock"))
        await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))
        return run_id
    old_run = await run_active()
    old = await get_judgment(tenant, request_id, old_run)
    await add_revision(tenant, request_id, "tester", 1, "두 번째 내용입니다.", [],
                       str(uuid4()), str(uuid4()))
    new_run = await run_active()
    new = await get_judgment(tenant, request_id, new_run)
    assert new_run != old_run
    assert old["judgment"]["id"] != new["judgment"]["id"]
    assert (await get_judgment(tenant, request_id, old_run))["judgment"]["id"] == old["judgment"]["id"]


async def test_judgment_api_scopes_runs_and_omits_source_without_permission(tenant):
    import httpx

    from jevtriage.auth.core import Principal, get_principal
    from jevtriage.main import create_app
    created = await create_request(tenant, "tester", "비민감 업무입니다.", [],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    run_id = (await get_request_meta(tenant, request_id))["active_run_id"]
    async def job(tx):
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                    tenant=tenant, run=run_id)).single(strict=True))["id"]
    async def handler(ctx):
        await execute_judgment(ctx, JevClient("", mode="mock"))
    await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(tenant, "tester", (), frozenset(), False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/requests/{request_id}/judgment")
        assert response.status_code == 200
        body = response.json()
        assert body["run_id"] == run_id and body["mode"] == "mock"
        assert all("source_text" not in evidence for output in body["outputs"]
                   for evidence in output["evidence"])
        history = await client.get(f"/api/requests/{request_id}/runs")
        assert history.status_code == 200 and history.json()["active_run_id"] == run_id
        app.dependency_overrides[get_principal] = lambda: Principal(tenant, "other", (), frozenset(), False)
        denied = await client.get(f"/api/requests/{request_id}/judgment")
        assert denied.status_code == 404


async def test_deadline_before_handler_marks_active_request_failed(tenant):
    from jevtriage.db.events import list_events
    created = await create_request(tenant, "tester", "기한 초과 시험입니다.", [],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    run_id = (await get_request_meta(tenant, request_id))["active_run_id"]
    async def age_and_job(tx):
        await (await tx.run("MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                            "SET r.created_at=datetime()-duration({seconds:2})",
                            tenant=tenant, run=run_id)).consume()
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                    tenant=tenant, run=run_id)).single(strict=True))["id"]
    job_id = await write_tx(tenant, age_and_job)
    await Worker(deadline_seconds=.1).process_job(tenant, job_id)
    assert (await get_request_meta(tenant, request_id))["status"] == "실패"
    assert any(e["kind"] == "judgment_failed" and e["run_id"] == run_id
               for e in await list_events(tenant))


async def test_expired_old_run_does_not_change_active_request(tenant):
    from jevtriage.db.events import list_events
    created = await create_request(tenant, "tester", "이전 실행입니다.", [],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    old_run = (await get_request_meta(tenant, request_id))["active_run_id"]
    async def age_and_job(tx):
        await (await tx.run("MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                            "SET r.created_at=datetime()-duration({seconds:2})",
                            tenant=tenant, run=old_run)).consume()
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                    tenant=tenant, run=old_run)).single(strict=True))["id"]
    job_id = await write_tx(tenant, age_and_job)
    from jevtriage.ingest.store import add_revision
    await add_revision(tenant, request_id, "tester", 1, "새 실행입니다.", [],
                       str(uuid4()), str(uuid4()))
    current = await get_request_meta(tenant, request_id)
    assert current["active_run_id"] != old_run
    await Worker(deadline_seconds=.1).process_job(tenant, job_id)
    after = await get_request_meta(tenant, request_id)
    assert after["active_run_id"] == current["active_run_id"]
    assert after["status"] == current["status"]
    assert not any(e["kind"] == "judgment_failed" and e["run_id"] == old_run
                   for e in await list_events(tenant))


async def test_real_span_citation_is_persisted_with_probability(tenant):
    from jevtriage.judgment.jev_client import ModelOutput
    class CiteClient(JevClient):
        def ask(self, state, question_map):
            if "is_evidence" in question_map:
                return ModelOutput(self.model, {"is_evidence": {"type": "noul", "noul": .9}},
                                   {"input_tokens": 0, "output_tokens": 0}, "mock", 0, 1)
            return super().ask(state, question_map)
    source = "공개 CSV를 월별 집계해 화면에 표시합니다."
    attachment = {"id": f"att_{uuid4().hex}", "filename": "request.md", "status": "ok",
                  "sha256": "a" * 64, "units": [{"location": {"line": 1}, "char_start": 0,
                  "char_end": len(source), "text_hash": "b" * 64, "text": source}]}
    created = await create_request(tenant, "tester", "판단해 주세요.", [attachment],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    run_id = (await get_request_meta(tenant, request_id))["active_run_id"]
    async def job(tx):
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                    tenant=tenant, run=run_id)).single(strict=True))["id"]
    async def handler(ctx):
        await execute_judgment(ctx, CiteClient("", mode="mock"))
    await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))
    async def citations(tx):
        return await (await tx.run("MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run})"
                                   "-[c:CITES]->(e:EvidenceSpan {tenant_id:$tenant,request_id:$request}) "
                                   "RETURN count(c) AS count,collect(c.prob) AS probabilities",
                                   tenant=tenant, run=run_id, request=request_id)).single(strict=True)
    result = await read_tx(tenant, citations)
    assert result["count"] >= 4
    assert all(prob == .9 for prob in result["probabilities"])


async def test_chat_text_is_persisted_and_cited_at_judgment_location(tenant):
    from jevtriage.judgment.jev_client import ModelOutput
    class CiteChatClient(JevClient):
        def ask(self, state, question_map):
            if "is_evidence" in question_map:
                return ModelOutput(self.model, {"is_evidence": {"type": "noul", "noul": .9}},
                                   {"input_tokens": 0, "output_tokens": 0}, "mock", 0, 1)
            return super().ask(state, question_map)
    text = "월별 주문량을 집계합니다. 결과는 운영 대시보드에 표시합니다.\n\n운영자는 매일 확인합니다."
    created = await create_request(tenant, "tester", text, [], str(uuid4()), str(uuid4()),
                                   datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    meta = await get_request_meta(tenant, request_id)
    run_id, revision_id = meta["active_run_id"], meta["latest_revision_id"]
    async def job(tx):
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                    tenant=tenant, run=run_id)).single(strict=True))["id"]
    async def handler(ctx):
        await execute_judgment(ctx, CiteChatClient("", mode="mock"))
    await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))
    async def evidence(tx):
        return await (await tx.run(
            "MATCH (e:EvidenceSpan {tenant_id:$tenant,request_id:$request,revision_id:$revision,source:'chat'}) "
            "OPTIONAL MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run})-[c:CITES]->(e) "
            "RETURN e,collect(c.prob) AS probabilities",
            tenant=tenant, request=request_id, revision=revision_id, run=run_id,
        )).data()
    rows = await read_tx(tenant, evidence)
    assert len(rows) == 3
    assert {json.loads(row["e"]["location_json"])["paragraph"] for row in rows} == {0, 1}
    for row in rows:
        span = row["e"]
        location = json.loads(span["location_json"])
        assert location["revision"] == 1 and location["sentence"] >= 0
        assert span["char_start"] < span["char_end"]
        exact_text = text[span["char_start"]:span["char_end"]]
        assert span["source_text"] == exact_text
        assert span["text_hash"] == hashlib.sha256(exact_text.encode()).hexdigest()
        assert row["probabilities"] and all(value == .9 for value in row["probabilities"])
    saved = await get_judgment(tenant, request_id, run_id)
    cited = [citation for output in saved["outputs"] for citation in output["citations"]]
    assert cited and all(citation["source"] == "chat" for citation in cited)


async def test_external_state_masked_but_saved_citation_uses_original_span(tenant):
    from jevtriage.judgment.jev_client import ModelOutput

    sensitive = "name@example.com"
    source = f"담당자 {sensitive}에게 월별 집계 결과를 보냅니다."
    created = await create_request(tenant, "tester", source, [],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    run_id = (await get_request_meta(tenant, request_id))["active_run_id"]

    async def job(tx):
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                    tenant=tenant, run=run_id)).single(strict=True))["id"]

    class InspectClient(JevClient):
        def __init__(self):
            super().__init__("", mode="mock")
            self.states = []

        def ask(self, state, question_map):
            self.states.append(state)
            if "is_evidence" in question_map:
                return ModelOutput(self.model, {"is_evidence": {"type": "noul", "noul": .9}},
                                   {"input_tokens": 0, "output_tokens": 0}, "mock", 0, 1)
            return super().ask(state, question_map)

    inspector = InspectClient()

    async def handler(ctx):
        await execute_judgment(ctx, inspector)

    await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))
    assert inspector.states
    assert all(sensitive not in json.dumps(state) for state in inspector.states)
    assert {unit["unit_id"] for state in inspector.states for unit in state.get("units", [])}
    saved = await get_judgment(tenant, request_id, run_id)
    assert saved is not None
    async def spans(tx):
        return await (await tx.run(
            "MATCH (e:EvidenceSpan {tenant_id:$tenant,request_id:$request,source:'chat'}) "
            "RETURN e.source_text AS text,e.id AS unit_id",
            tenant=tenant, request=request_id)).data()
    rows = await read_tx(tenant, spans)
    assert any("name@example." in row["text"] for row in rows)
    cited = {citation["id"] for output in saved["outputs"] for citation in output["citations"] if citation}
    assert cited.intersection(row["unit_id"] for row in rows)
