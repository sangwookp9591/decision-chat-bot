# 영속 worker와 실행 추적

T08 구현 메모, 2026-10-03.

## 실행

`make up`으로 Neo4j를 켠 뒤 `make worker`를 실행한다. 직접 실행할 때는 저장소 루트에서 `cd backend && .venv/bin/python -m jevtriage.jobs.worker`를 사용한다. `--concurrency`, `--lease-seconds`, `--poll-seconds`, `--deadline-seconds`, `--max-attempts`로 처리 수·lease·폴링·실행 한도를 지정한다. 기본값은 각각 2, 15초, 0.5초, 120초, 3회다. SIGINT/SIGTERM을 받으면 새 Job을 받지 않고 진행 중 핸들러가 끝날 때까지 기다린다.

worker는 `pending` Job과 lease가 만료된 `running` Job을 검색한 뒤 `db.jobs.claim_or_takeover`로 소유권을 얻는다. 소유권 확인, 단계 기록, 실행 종료는 쓰기 트랜잭션에서 처리한다. heartbeat가 실패하면 핸들러 태스크에 취소 신호를 보내고 이후 정식 커밋을 막는다. 외부 호출은 중복될 수 있으므로 핸들러는 결과 저장 전에 `ctx.commit`을 사용해야 한다.

## 핸들러 계약

제품 핸들러는 실행 시 `register(kind, async_handler)`로 등록한다. 테스트용 kind는 테스트에서만 `Worker(handlers={...})`로 주입한다. Job의 `kind` 또는 Run의 `job_kind`가 핸들러를 선택한다. 핸들러는 `ctx.run_id`, `ctx.request_id`, `ctx.revision_id`, `ctx.tenant_id`, `ctx.attempt_id`, `ctx.versions`를 사용한다.

`async with ctx.step(name, kind="code")`가 단계 시작·종료를 기록한다. kind는 `ai`, `code`, `rule`, `external`, `human` 중 하나다. 건너뜀과 사람 대기는 `completion_status="skipped"` 또는 `"waiting_human"`을 지정한다. `ctx.commit(async_fn, affects_request=True)`는 활성 실행 확인 후 Job 소유권을 같은 트랜잭션에서 검증한다. 요청의 최신 결과 포인터, 검토·배정 대상, 사용자 이벤트 같은 요청 범위 쓰기에는 `affects_request=True`를 반드시 지정한다. 핸들러가 정식 판단을 저장한 후 정상 반환하면 Run은 `judgment_saved`, Job은 `completed`가 된다. 핸들러는 사용량을 `ctx.record_usage(...)`로 attempt에 남길 수 있다.

## 보존·복구

Run의 `versions_json`은 첫 시도에 고정된다. 기존 Run의 policy/config/model/qset/schema/catalog 버전을 읽고 이후 인계에서 바꾸지 않는다. `attempts_json`에는 시도별 ID, generation, 시작·종료, 오류, 사용량이 남는다. lease 만료 후 새 시도는 이전 attempt를 `interrupted`로, 열린 RunStep을 `failed` 및 `LeaseExpired`로 닫는다. Run의 `started_at`과 deadline은 재시작 후에도 유지한다. 총 deadline 또는 최대 시도 초과는 실패로 종료한다. 실패한 Run은 이후 성공·취소로 재분류하지 않는다.

`get_trace(tenant_id, run_id)`는 Run과 RunStep을 반환한다. 입력·출력 요약에는 원문이나 모델 전송본문을 넣지 않는다. 단계·실행 종료와 소유권 상실은 독립 JSONL journal에도 attempt ID로 기록한다. 인계된 worker가 늦게 돌아오면 정식 단계·결과·이벤트 대신 소유권 상실 진단만 남긴다.

현재 T08은 worker 기반과 Trace 저장 함수까지 제공한다. 실제 판단 핸들러 연결은 T09, Flow/Topology 조회 API와 화면은 T17 소유다.
# Tenant-scoped workers

Worker processes can be limited to selected tenants for isolated tests and E2E runs:

```sh
python -m jevtriage.jobs.worker --tenant t-alpha --tenant t-beta
```

The repeatable `--tenant` option takes precedence over `WORKER_TENANTS`. Set the environment variable to a comma-separated list when the CLI is not convenient:

```sh
WORKER_TENANTS=t-alpha,t-beta python -m jevtriage.jobs.worker
```

When neither is set, a worker retains the default cross-tenant discovery behavior. Give each parallel test/E2E worker a distinct tenant allowlist so it cannot lease another run's Jobs.
