# FIX-FAULT 검증 기록

2026-10-04 UTC. 현재 작업 트리에서 실행했으며 커밋하지 않았다.

| 항목 | 수정 전 재현 | 수정·계약 | 수정 후 검증 |
| --- | --- | --- | --- |
| SIGSTOP 뒤 Job 인계 | [003529](20261004T003529Z/pytest.log): 전체 10/11, handoff 35초 시간 초과. `SHOW TRANSACTIONS`에서 B의 `claim_next`가 A의 열린 트랜잭션에 27초 이상 `Blocked by`였고 서버 `db.transaction.timeout=0s`였다. [004318](20261004T004318Z/worker_b.log): 시간 제한 도입 후 B가 `Neo.ClientError.Transaction.LockClientStopped`로 종료됐다. | `write_tx`/`read_tx` 기본 및 호출별 시간 제한, `claim_next` 1초 제한과 종료된 잠금 재시도, Compose 서버 제한 7초/6초. 만료 Job의 빈 폴링 재검색 시험과 잠금 대기 시간 제한 시험을 추가했다. | [005424](20261004T005424Z/report.md), [005747](20261004T005747Z/report.md): 연속 2회 각각 11/11, handoff generation `[1,2]`, SIGKILL 복구 통과. |
| 종료 journal 내구성 | [004711](20261004T004711Z/pytest.log): handoff는 통과했으나 관측 대조에서 직전 SIGKILL 복구 Run의 `run_commits_missing_journal` 1건. 새 단위 시험에서 `worker_run`의 `append()` 직후 파일 미기록을 확인했다. | 핵심 수신·종료·판정 레코드는 그룹 커밋 큐에서 fsync 완료까지 기다린다. 진행·전달 레코드는 비동기 묶음으로 남긴다. fsync 대기와 오류 전파 시험을 추가했다. | 두 최종 실행에서 `run_commits_missing_journal=[]`; 전체 백엔드 420 통과·1 skip, Ruff 0건. |

Neo4j 커밋과 로컬 journal 쓰기는 원자적이지 않다. 커밋 직후 append 전 강제 종료 가능성은 남으며, `reconcile_commits`가 이 경우를 누락으로 표시한다. 이번 변경은 append 반환 뒤의 버퍼 유실을 막는다. 프런트 파일을 수정하지 않아 프런트 검증은 실행하지 않았다.
