# P5 잔여 결함 수정 재검증

- 대상: 시작·종료 HEAD `4c43e72`, 2026-10-04 01:46–01:57 KST.
- 실제 Playwright Chromium **153.0.8010.12**, WebKit **26.6**. P4와 같은 로컬 개발 DB/역할/요청을 사용했다. 제품 코드·문서·설정 수정 없음; 산출물은 이 보고서와 `p5-*.png`뿐이다.
- OrbStack 공유 Neo4j(7687) 재사용, API 8691 / Vite 5891, `JEV_MODE=live`, worker `--tenant t-alpha --tenant t-beta`, 절대 `.data` 경로. collector/watchdog은 후반 추가 기동 후 Monitoring을 재측정했다. 외부 입력은 비민감 가상 회의실 요청이다.
- 판단 기준: P4 REPORT의 재현 단계, PRD/TASK, spec 00–08 및 아키텍처/운영 문서 중 관련 계약. 특히 DATA_MODEL:30의 `block_reasons` 시작 차단, EXECUTION_CONTRACT의 승인·배정 경계, LEARNING_VALIDATION의 저장 판단 섀도 검증을 대조했다. 전체 게이트 재인수 시험은 아니다.

## 항목별 판정

**7개 항목 중 해결 5, 부분 해결 2.** P4-05/P3-13은 개선됐으나 일반 화면 내부 코드 노출이 남는다. 새 기능 결함은 관찰하지 않았다. 아래 코드 노출은 기존 결함의 잔여 범위로 집계하며 신규 결함으로 중복 계산하지 않는다.

| 항목 | 판정 | Chromium·WebKit 재수행 결과 |
|---|---|---|
| P4-01 차단 이유 | 해결 | 기존 `task_8f9892a1fb5c450ba5530a9fa3863339` 선택. 목록·상세에 “개발 가능성 또는 수행 전제가 아직 해결되지 않았습니다.” 표시, “진행으로 변경” disabled=true. [C](p5-c-block.png) / [W](p5-w-block.png). |
| P4-02 학습 빈 날짜 | 해결 | 검증 중 `R-PFIVE-01@1`에서 시작 삭제 → “시작과 끝 날짜를 모두 올바르게 입력해 주세요.” 및 실행 비활성. 유효 날짜 복구 → 각 브라우저 실제 POST /validate 200, 완료 결과. pageerror 0. [C 빈 날짜](p5-c-empty-date.png) / [W 빈 날짜](p5-w-empty-date.png), [C 결과](p5-c-validated.png) / [W 결과](p5-w-validated.png). |
| P4-03 권한 없는 상세 오류 소실 | 해결 | team_member가 P4의 review_id 직접 접근. 실제 목록 응답의 상태/본문은 그대로 두고 전달만 800ms 지연. 상세 오류가 먼저 나타난 뒤 목록 완료 및 새로고침 이후에도 “검토를 찾을 수 없습니다.”와 “목록으로 돌아가기” 유지. [C](p5-c-denial.png) / [W](p5-w-denial.png). |
| P4-04 선택 결과·검토 상세 넘침 | 해결 | 같은 P4 요청 A의 이전 실행 비교가 있는 Main, 처리된 Review 상세를 선택하여 두 너비 실측. 모든 측정에서 viewport=scrollWidth. 아래 표 참조. |
| P4-05 일반 화면 내부 코드 | 부분 해결 | Main 검토 사유, Review 판단/유형/위치, Monitoring 기존 영어 알림·사유, 학습 승인 이력의 approve/원시 JSON은 개선. 그러나 학습 신호 이름·효과 설명, 판단 맵 노드, 업무 전제, Main 신뢰도 문구가 남음. 아래 잔여 결함 참조. |
| P3-12 모바일/입력 우선 | 해결(이번 표본) | 입력이 목록보다 앞에 있음. 7개 화면, 2브라우저×2너비 총 28측정 모두 통과. 신규 검증 결과 학습 화면도 375/520 추가 측정 통과. |
| P3-13 코드/영문 | 부분 해결 | P4-05와 동일한 잔여 범위. Trace의 명시적 기술 상세와 추적용 UUID 자체는 이번 결함에 포함하지 않음. |

## scrollWidth 실측

높이 900px. 각 셀은 **375px / 520px** viewport 순서이며 documentElement와 body를 함께 검사해 같은 값이었다. C/W Main은 모두 동일한 요청 A와 두 실행 비교 상태를 사용했다. Observatory는 실제 저장 Flow와 선택 run, JudgmentMap은 실제 관계가 로드된 모바일 목록 상태다.

| 화면 | Chromium | WebKit | 375px 증거 C / W |
|---|---|---|---|
| Main 선택 결과 | 375 / 520 | 375 / 520 | [C](p5-c-Main-375.png) / [W](p5-w-Main-375.png) |
| Review 선택 상세 | 375 / 520 | 375 / 520 | [C](p5-c-Review-375.png) / [W](p5-w-Review-375.png) |
| Monitoring | 375 / 520 | 375 / 520 | [C](p5-c-Monitoring-375.png) / [W](p5-w-Monitoring-375.png) |
| Learning 후보·버전·결과 | 375 / 520 | 375 / 520 | [C](p5-c-Learning-375.png) / [W](p5-w-Learning-375.png) |
| Tasks 목록 | 375 / 520 | 375 / 520 | [C](p5-c-Tasks-375.png) / [W](p5-w-Tasks-375.png) |
| Observatory | 375 / 520 | 375 / 520 | [C](p5-c-Observatory-375.png) / [W](p5-w-Observatory-375.png) |
| JudgmentMap | 375 / 520 | 375 / 520 | [C](p5-c-JudgmentMap-375.png) / [W](p5-w-JudgmentMap-375.png) |

## 잔여 결함 상세

### P4-05/P3-13 [심각도 낮음] 일반 화면 — 내부 신호·결정 코드와 영어 문구 잔존 — 예상 규모 S

- **재현:** (1) rule_admin `/learning?rule_id=R-PFOUR-01`에서 확정 범위·수명·게시 후 관찰 읽기. (2) operator `/judgment-map?request_id=req_e83022236db54a85950d9c5de402171d`의 모바일 노드 목록 읽기. (3) 같은 요청 Main 결과 및 team_member 업무 목록 읽기. 자세히를 펼치지 않아도 보이며 C/W 동일하다.
- **근거:** Learning `신호 ai_team_involvement`, `business_involvement`, `clinical_safety` 등과 `APPLIED used/out_of_scope`, `shadow 제외`; JudgmentMap `Jev · lead_org`, `Jev · ai_need`, `검토 결정 · approve/request_info`, `규칙 결정 · approve`; Tasks `정책 임계값(risk_clear_max)`; Main `Choice confidence 73%`. 위 표의 해당 스크린샷에 표시된다. Observatory 기본 Flow의 단계명·상태·연결은 한국어로 표시됐고 이번 표본에서는 추가 원형 코드 노출을 찾지 못했다.
- **위치:** `frontend/src/pages/learning/learningModel.ts:80`은 `p.signal`을 그대로 연결한다. `backend/jevtriage/graph/model.py:79`, `:97`, `:102`는 question_id/action을 제목에 직접 삽입한다. `frontend/src/pages/Main.tsx:162`는 `Choice confidence`를 직접 출력한다. `frontend/src/pages/Tasks.tsx:12`는 원래 전제 설명을 그대로 보여 준다.
- **제안 수정:** 학습 신호를 기존 `questionLabel`로 번역하고 효과 설명의 기술 용어를 한국어 사용자 문구로 바꾼다. 맵 제목·요약·상태에도 질문/결정/필드 매핑을 적용하고 원형 키와 JSON은 접힌 기술 상세로 옮긴다. Main은 “선택 확신도”, Tasks 전제의 정책 키는 “위험 허용 기준”처럼 사용자 표현으로 표시하되 원본 데이터는 보존한다. 위 4개 화면의 실제 저장 데이터 표본으로 회귀 확인한다.

## 이전 해결 항목 회귀

기존 해결 항목 중 가벼운 회귀 후보군 P3-01/04/05/06/09/11에서 무작위로 3개를 추출했으며 선택은 **P3-09, P3-01, P3-06**이었다. 전체 11개에서 균등 표본을 뽑은 것은 아니다.

| 항목 | C/W 결과 |
|---|---|
| P3-09 Monitoring 빈 날짜 | 시작 비움 → “시작과 종료 시각을 모두 올바르게 입력해 주세요.” 및 적용 disabled=true, pageerror 없음. |
| P3-01 로그인 | 새 쿠키 컨텍스트 `/tasks`에서 잘못된 암호 → 한국어 오류·원 URL 유지. 올바른 암호 입력 → 같은 `/tasks`로 로그인 성공. |
| P3-06 검증 직렬화/기간 | 실제 새 검증에서 지정 기간·39표본·“AI 필요성 → 혼합 9건”·실패 0 표시. 문자열 문자 인덱스 없음. |

추가로 P3-05 채팅 보내기 즉시 요청 textarea 전달/닫힘, P3-11 선택 request_id 새로고침 후 결과 복원을 C/W 모두 확인했다. 브라우저 pageerror는 전체 관찰에서 0건이다. 자동화 도중 locator strict/timeout 오류는 있었으나 제품 pageerror와 구분했고, 해당 시도는 성공 증거로 계산하지 않았다.

## 데이터·검증 및 정리

- P4 재사용: 요청 A `req_e83022236db54a85950d9c5de402171d`, review `rvw_473ae391e3c44669930c75751112ada3`, run `run_021dac6abc95436f9a5520943a02d493`, 차단 업무는 위 표 참조.
- 새 LIVE 요청 6건을 UI 접수·수정 승인했다. 첫 3건(담당 조직 IT팀→현업)은 기존 승인 후보와 같은 묶음이라 새 검증 버전 준비로 이어지지 않았다. 추가 3건 `req_d45366afff054f2689bfd70ab20259b6`, `req_7926529f72f04a28aabd2bf2fc84534e`, `req_3660385ddaec48e6b49ea2417946c102`의 AI 필요성 불필요→혼합 수정 승인으로 새 후보를 만들었다.
- 후보 `cand_ebddb68698b96a3adf8ec88c`(지지 3/반례 5) → UI 승인 → `R-PFIVE-01@1` 검증 중 버전 생성. 게시하지 않았다. 이 수정값은 제품 품질 정답이 아니라 검증 준비용 가상 결정이다.
- C 검증 `val_eddd4cad317f403c8e662ca373f3ae0b`, W 검증 `val_70726802f67c4ae682bbd5e34c3a2569`. 각각 UI 2026-10-01 00:00–10-05 00:00, 저장 UTC 09-30 15:00–10-04 15:00, 39표본·정답 16·변경 9·실패 0·부작용 0·모델 호출 0. 저장 판단에 대한 실제 섀도 규칙 재평가이며 새 Jev 재호출 검증은 아니다.
- 최종 활성 정책 **v17, rules=[]** 유지. 가상 요청·수정/승인·내부 배정 업무·후보·검증 감사 기록은 개발 DB에 남겼다. 임의 삭제나 과거 기록 수정은 하지 않았다.
- 종료: C/W 브라우저 닫음; 이번에 시작한 API 57866, worker 57867, Vite 57868, collector 65032, watchdog 65033 및 임시 조작기 종료. 8691/5891/15995 LISTEN 없음 확인. 공유 Neo4j healthy/7687 유지. Docker Desktop 실행·공유 Neo4j 정지 없음.
