# 접수 API

T06 API 초안 구현 계약. 모든 경로는 `/api` 아래이며 인증된 세션을 사용한다. 쓰기 요청은 `X-CSRF-Token` 및 `jev_csrf` double-submit 검증을 통과하고 `Idempotency-Key`를 제공해야 한다.

## 경로

| 메서드/경로 | 입력과 결과 |
| --- | --- |
| `GET /meta` | Jev mode, 접수 한도, API 버전 |
| `POST /requests` | multipart `text`, 최대 5개 `files`, Idempotency-Key. request ID, revision 번호, 상태 반환 |
| `GET /requests` | 본인·공유 조직·운영자 범위, 상태·기간·페이지 필터 |
| `GET /requests/{id}` | 요청, revisions, 첨부 메타데이터 |
| `POST /requests/{id}/file-decision` | JSON `exclude` attachment ID 배열, `expected_revision`; 새 revision 및 판단 실행 생성 |
| `POST /requests/{id}/revisions` | multipart 텍스트/첨부 및 `expected_revision`; 이전 결과를 유지하고 새 revision 생성 |
| `GET /requests/{id}/evidence/{span_id}` | `can_read_source`인 주체에게만 원문 span 반환 |

파일 파싱·임시 저장은 `ingest.parsers.parse_file`과 `ingest.files.store_upload`가 담당한다. 거절 첨부가 남은 revision은 `needs_file_decision`이며 Job을 만들지 않는다. 접근 범위 밖 ID는 404로 응답한다.

각 InputRevision에는 채팅 원문을 문장 단위 `EvidenceSpan`으로 저장한다. `source='chat'`, `location_json`의 revision/paragraph/sentence, revision 원문 기준 `char_start`/`char_end`, 문장 SHA-256, 정확한 `source_text`를 보존한다. 첨부 span은 기존처럼 `attachment_id`와 파일 위치를 가진다. 판단은 저장된 span ID를 Jev 근거 단위로 사용한다.

API 접수 journal은 DB 쓰기 전 `request_received`, 처리 종료 시 완료/실패 이벤트를 attempt ID로 남긴다. 허용 journal 필드 외의 원문, 파일명, 키, 쿠키를 쓰지 않는다. 상세 운영 SLO와 보완/retry 분모는 [05_SLO 보완·재실행 측정 규칙](../spec/05_SLO.md#보완재실행과-측정-단위)을 따른다.

## 검증 상태

완료 증거: `make up && cd backend && .venv/bin/pytest -q --tb=short` 실행 결과 55 passed, 1 skipped. `tests/integration/test_ingest_api.py`에서 TestClient/httpx를 통해 실제 앱 라우터와 세션 인증을 검증한다. HTTP 시험은 CSRF·역할·tenant·원문 권한, 동일/상이 payload 멱등키, stale revision, PDF/DOCX/MD 위치 단위 보존, 손상 파일 제외 뒤 새 revision/Job 생성, DB 쓰기 실패 503과 attempt journal 종료 레코드를 확인한다. 보완 revision 이후 `first_received_at` 및 `first_supported_revision` 불변도 저장소의 실제 Neo4j 기록으로 확인한다. 상세 실행 증거는 TASK T06 행을 참조한다.
