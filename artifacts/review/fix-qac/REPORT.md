# FIX-QAC — QA-C 확정 결함 6건 수정

2026-10-05. 담당 코드·제품 회귀 시험·JEV_CONTRACT/AUTH/REVIEW_ASSIGN 문서를 수정했다. commit/push, docs/spec, evaluation 및 프런트 수정은 하지 않았다. 기준 보고서는 `artifacts/review/qa-full/qa-c/REPORT.md`이다.

## 수정 전 실패 → 수정 → 통과

| 항목 | 수정 전 제품 재현 | 수정 | 수정 후 검증 |
| --- | --- | --- | --- |
| QA-C-02 / P0 | 일반 판단 대조는 통과, 실제 섀도 페이로드에 합성 5종 원문 노출로 실패; 직접 Jev 전송도 실패 | 공용 MaskingClient를 일반 서비스·섀도·pipeline에 적용하고 JevClient.ask에도 같은 구현으로 기본 전송 경계 적용; 고정 정책 설정, 중첩 state·질문 설명·운영 가이드를 복사·마스킹 | 일반·섀도 모두 이메일·전화·주민번호·Luhn 카드·키 패턴 원문 0건; 직접 전송·미래 중첩 state·질문 설명 통과; 원본 섀도 재현 통과 |
| QA-C-01 / P1 | 로그인/정책/검토/업무 422에 제출 표본 반사; ctx의 ValueError 원문으로 직렬화 실패 | 공통 RequestValidationError 응답에 loc/type/msg만 유지, input/ctx 제거; custom ValueError/AssertionError 메시지도 일반화 | 제품 5개 경로와 ctx 시험 통과; 원본 5개 경로 재현 통과 |
| QA-C-05 / P1 | 로그인 1e1000/NaN/Infinity/-Infinity 4건 500; 추가 임의 중첩 config 시험 4건은 200으로 잘못 수락 | JSON 본문 경계에서 overflow float와 비표준 비유한 상수 거부; 안전한 검증 응답과 함께 적용 | 로그인 및 중첩 config 모두 400; 원본 숫자 재현 4건 통과 |
| QA-C-03 / P1 | policy version 및 graph config_version의 int64 상한/하한 초과 6건이 저장소 호출에 진입하여 실패 | 공용 domain.api_types.Int64 적용: 정책 경로/게시/rollback, graph config_version, review 버전/offset; 기존 추가 제약 유지 | 모든 범위 초과 422 및 저장소 호출 0건; 원본 큰 정수 재현 3건 통과(learning 문자열 버전 경로는 기존 200 유지) |
| QA-C-04 / P1 | 더 최근 타 조직 100건 뒤의 허용 검토 누락: 정규 ID·AI팀/IT팀/현업/검토자 별칭 5건 실패 | reviewer 역할과 상세와 같은 조직 해석을 적용하여 Cypher WHERE에 넣고 정렬·SKIP·LIMIT; 선택적 limit/offset 추가 | 다섯 조직 표현에서 상세 200 + 목록 포함; operator-only 빈 목록; 원본 101건 starvation 재현 통과 |
| QA-C-06 / P1 | classifications 목록·draft_tasks 문자열 항목·배열 method가 500으로 3건 실패; 기타 잘못된 값 3건은 대조군 422 | 분류/업무/changes의 중첩 Pydantic 모델, 필드 타입·허용 이름/값 검증; 기존 명령 필드 이름 유지 | 잘못된 6개 구조 모두 422; Review 상세 전체 불변 및 Assignment/Task/Correction/ReviewDecision 생성 0건; 원본 nested 재현 통과 |

초기 제품 묶음은 [before.log](before.log)에서 **26 failed, 4 passed**였다. 이 중 reanalyze 1건은 시험의 CSRF 준비 누락으로 403을 받아 실패한 harness 문제이며, 나머지 **25건은 실제 제품 결함 재현**이다. CSRF fixture를 원본 QA 방식으로 보완했고 원본 reanalyze를 포함한 QA-C-01 재현도 모두 통과했다. 추가 비유한 중첩 설정은 [nonfinite-before.log](nonfinite-before.log)에서 **4 failed**를 확인한 뒤 본문 guard를 적용했다.

현재 제품 전용 묶음은 [after.log](after.log)의 **35 passed**다. 마지막 1건은 SDK import/system_one이 guarded JevClient에만 존재하는지를 검사하는 구조 계약이다. 새 시험 코드의 키 패턴은 런타임 조합으로 만들며 키 리터럴을 추가하지 않았다.

## 원본 QA 재현

원본 실패 증거를 덮어쓰지 않도록 `qac_evidence_plugin.py`와 별도의 `original-evidence/`를 사용했다.

- [original-probes.log](original-probes.log): 원본 `test_api_error_redaction.py`, `test_api_numeric_errors.py`, `test_shadow_masking.py` **10 passed**. 테스트 함수는 수정하지 않았다.
- [original-runtime-probes.log](original-runtime-probes.log): 원본 `test_api_robustness.py`의 큰 정수 3건·nested 변경 1건과 `test_review_queue_starvation.py` 1건 **5 passed**. `original-repro/test_original_repros.py`는 원본 함수와 parametrize를 그대로 로드한다.
- 후자의 `runtime`은 원래 전용 7688/API subprocess fixture 대신 **ASGI 실제 API·실제 Neo4j·실제 Worker.process_job**을 이용한다. 단일 무작위 tenant만 시드/삭제하고 CSRF 세션은 결정적 fixture다. 별도 HTTP 서버나 DB를 시작하지 않았으므로 원본 QA의 두 API 프로세스/네트워크 전달 시험을 다시 실행했다는 의미는 아니다. 초기 async marker 및 Job 조회 조건의 harness 오류를 보완한 뒤 위 최종 5건을 확인했다.

실행 명령:

```sh
cd backend
.venv/bin/pytest -q tests/unit/test_qac_api_boundaries.py \
  tests/unit/test_qac_external_boundary.py tests/integration/test_qac_regressions.py
PYTHONPATH=.:../artifacts/review/fix-qac JEV_MODE=mock .venv/bin/pytest -q \
  -p qac_evidence_plugin \
  ../artifacts/review/qa-full/qa-c/repro/test_api_error_redaction.py \
  ../artifacts/review/qa-full/qa-c/repro/test_api_numeric_errors.py \
  ../artifacts/review/qa-full/qa-c/repro/test_shadow_masking.py
PYTHONPATH=. JEV_MODE=mock JEVTRIAGE_STRICT_TENANT=1 .venv/bin/pytest -q \
  ../artifacts/review/fix-qac/original-repro
.venv/bin/pytest -q
.venv/bin/ruff check jevtriage tests
.venv/bin/lint-imports
```

## 통합 검증

- [pytest-full.log](pytest-full.log): 전체 **530 passed, 1 skipped**, 88.26초. 전송 구조 계약 1건을 추가하기 전의 전체 결과다.
- [pytest-full-final.log](pytest-full-final.log): 최종 전체 **531 passed, 1 skipped**, 125.54초. SDK 전송 구조 계약도 포함한다.
- [ruff.log](ruff.log): `ruff check jevtriage tests` **All checks passed**.
- [imports.log](imports.log): 기존 import 계약 **6 kept, 0 broken**. 소유 범위를 지키기 위해 pyproject 계약 정의는 수정하지 않고 제품 AST 시험으로 SDK 전송 경계를 추가했다.
- `git diff --check` 통과. AUTH/JEV_CONTRACT/REVIEW_ASSIGN 관련 절 갱신.

## 범위·제한

이번 FIX-QAC의 확정 결함 6건은 모두 구현·재현 검증했다. 실 Jev 품질 시험은 자격 증명과 live 실행 게이트 때문에 기존 전체 시험에서 1건 건너뛴다. QA-C의 부하·backup/restore·Redis/다중 API·기존 fault scenario는 이번 경계 수정의 재현 시험에 해당하지 않아 다시 실행하지 않았다. 프런트 코드를 수정하지 않아 프런트 typecheck/test/build는 이 작업의 검증 대상이 아니다.

공유 Neo4j 7687은 정지하지 않았고, 작은 무작위 tenant 시험만 사용했으며 지연이나 DB timeout을 관찰하지 않았다. Docker/Desktop/8191/5391 프로세스를 건드리지 않았다. 공유 트리의 다른 작업자 변경(`backend/tests/fault/scenarios.py`, `scripts/fault/run.sh` 등)은 이 작업의 수정 목록에 포함하지 않는다. 통합 시험은 실행 시점의 공유 트리를 검증한 것이며 이후 병합·커밋은 코디네이터 소유다.
