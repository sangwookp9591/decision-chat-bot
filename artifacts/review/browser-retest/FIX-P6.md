# FIX-P6 — 초안 버전 구분 표시(P6-01)와 라벨 잔여 2건 (UX-5)

## 1. 재현 시험(수정 전 실패 확인)
- `backend/tests/integration/test_review_assignment.py::test_judgment_api_shows_only_current_draft_version` (2 케이스: 분류만 수정 승인 / 업무 조직 수정 승인). 수정 전: `draft_tasks`가 `[('draft-1',1),('draft-1',2)]`(같은 업무 v1·v2 동시 반환)로 실패(`AssertionError … Left contains one more item`). 수정 후 통과.
- 시험 fixture의 Judgment에 실제 파이프라인이 쓰는 `author`를 보강했다(API 직렬화가 요구).

## 2. 수정
- `judgment/store.py`: Draft 단위로 업무를 묶어 조회, `draft_source`(v1=`ai`, 이후=`reviewer`)·`draft_created_by` 도우미.
- `judgment/api.py`: `draft_tasks` = 현재 초안 버전(최신 Review가 approved면 승인된 `draft_version`, 아니면 최신 버전)의 업무만. 추가 `current_draft_version`, `draft_versions[{draft_version,source,created_by,created_at,tasks}]`. 필드 이름 유지.
- `review/api.py`: 각 `drafts[]`에 `source`·`created_by`, 최상위 `original_draft`·`current_draft` 추가(권한 코드 불변).
- 프런트: `pages/main/DraftVersions.tsx`(버전 비교 컴포넌트, 원안 대비 변경 항목 표시) → Main은 현재 버전만 “업무 분담 (v2 검토자 수정안)”으로 표시하고 “원안과 비교” 펼침에 버전별 표시. Review는 현재 초안만 편집 대상으로 보이고 “AI 원안” 값은 `original_draft`에서, 처리된 검토는 같은 비교 펼침. (기존에 범용 diff 컴포넌트는 없어 새로 만들어 두 화면이 공유.)
- 라벨: `comparisonConditionsLabel`로 효과 설명을 “실제 실행 / 규칙 적용·범위 밖 집단 / 비교 검증 실행 제외”로, “섀도 실행 N건” → “비교 검증 실행 N건”. JudgmentMap 묶음 라벨에 `KIND_LABEL` 적용(`ModelOutput 외 22개` → `Jev 반환값 외 22개`; 기존 사전 값 사용), 사전의 `ValidationRun: 섀도 검증` → `비교 검증`.
- 영향 조사: `draft_tasks`를 읽는 곳은 프런트 Main·Review와 백엔드 내부(서비스·시험)뿐이다. WebMCP·eval 러너는 이 API 필드를 쓰지 않는다(grep 확인). acc_a 시험이 쓰는 검토 상세 `drafts`는 구조 유지(필드 추가만).
- docs: `JUDGMENT_STORE.md`, `REVIEW_ASSIGN.md`에 절 추가.

## 3. 검증
- `backend/.venv/bin/pytest -q`: 395 통과·1 건너뜀. `ruff check jevtriage tests`: 0건.
- 프런트: `typecheck` 통과, `vitest` 97 통과(신규: Main 버전 비교, Review 현재 초안·원안 구분, 라벨 문장), `build` 성공.
- 브라우저(API 8891·Vite 6091·`--tenant t-alpha` worker·`JEV_MODE=live`, 공유 Neo4j, Chromium·WebKit 각각): 
  - 분류만 수정 승인 `req_d927355da484450bbb782cbfbc7e2f57`, 업무 조직 수정 승인 `req_5f79768aa7d349abb9dfee2efa89bc8d`. 두 요청 모두 API `draft_tasks=[draft-1 v2]`, `draft_versions=[v1 ai, v2 reviewer]`. Main “업무 분담” 1줄, 제목 “(v2 검토자 수정안)”, “원안과 비교”에 v1·v2 표시, 조직 수정 건은 “원안 대비 변경: 주관, 협업”. Review 처리 완료 화면도 업무 1건·AI 원안 값 유지·비교 펼침 확인. pageerror 0. 스크린샷 `fix-p6-shots/`.
  - Learning `/learning?rule_id=R-PFOUR-01`에 새 문장 표시, shadow/APPLIED 원문 0. JudgmentMap 목록·지도 모두 “Jev 반환값 외 22개”.
  - `responsive-overflow.spec.ts` 375/520px 28건: 27 통과, `375px Monitoring` 1건이 첫 실행에서 시간 초과(미변경 페이지) → 단독 재실행 시 Chromium·WebKit 통과(일시적 지연으로 판단).
- 부수 발견: 질문 문구에 따라 live Jev가 `lead_org:'미정'` 초안을 만들면 승인 자체가 “담당 조직이 tenant 범위에 없습니다”(422)로 막힌다(기존 동작, 이번 범위 밖). 검증용 요청 `req_36deec77…`는 검토 대기로 남겼다.
- 정리: 내 API·worker·Vite 종료. 공유 Neo4j(7687)·8191/5391 프로세스는 건드리지 않음. 가상 요청 3건·감사 이력이 개발 DB에 남음.

## 4. 건너뜀
- 없음. (`created_by`는 v1이 `catalog:catalog-v2` 같은 내부 값이라 화면에서는 “AI 자동 생성”/“검토자 수정”으로만 표기하고 API에는 원값 유지.)
