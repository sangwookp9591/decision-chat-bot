# VERIFY-P8 — P7 수정 재검증

2026-10-04 KST · 커밋 `0624e3a11696d6d828953ec6ab206223f466eee5` · 제품 코드/문서/설정 변경 없음.

**결론: F1·F2·F3·F4·F6의 핵심 결함은 해결 확인, F5는 개선됐으나 부분 미해결.** 양방향 업무 차단과 최종 결과 표시를 두 브라우저에서 확인했다. 새로 확정한 제품 결함은 없으며, WebKit 자동 스크롤 직후 클릭 누락은 원인 구분이 필요한 불확실 관찰로 분리했다.

## 환경·측정 범위

- Chromium 153.0.8010.12 / WebKit 26.6, 설치된 Playwright, 1440×1100. API 8991, Vite 6291→8991, `JEV_MODE=live`, 절대 DATA_DIR의 기존 비민감 데이터, Redis DB0, worker `--tenant t-alpha --tenant t-beta`, collector·watchdog. OrbStack 공유 Neo4j/Redis는 정지하지 않았다.
- 인증은 실제 로그인 API, 업무 동작은 실제 UI(입력·제출·수정 승인·진행 전이). 판단·SSE·모니터링 응답 mock/지연 주입 없음. t-alpha 합성 요청/검토/업무를 사용했다. 서버 차단 확인만 같은 사용자로 직접 transition API를 호출했다.
- 기준: VERIFY-P7 F1–F6, PRD R06/R07, spec/02·05·06, architecture/EXECUTION_CONTRACT·IMPLEMENTATION·DATA_MODEL·REVIEW_ASSIGN·PROGRESSIVE_RESULTS, operations와 최종 GATE_REPORT의 검증 구분. 외부 완료 요건은 재나열하지 않는다.
- 요청 시점은 capture click 이벤트의 `performance.now()`, 잠정은 `.provisional-badge`, 최종은 `.result-stack:not(.provisional-result) .summary-text` 표시. 수정 후 잠정에도 “판단 결과” h2가 있으므로 **P7의 h2 선택자를 그대로 쓰면 잠정을 최종으로 오측정**한다. DOM 삽입 시간이며 paint나 공식 서버 SLO가 아니다.
- 콜드는 회마다 새 Vite 프로세스·빈 cacheDir·새 context·실제 로그인 후 `/monitoring` 직행(각 엔진 3회). DB/OS 캐시는 초기화하지 않았다. navigation start부터 MutationObserver가 제목/필터 및 영역 `aria-busy=false`를 관측한 ms다. P7의 goto 직전 외부 시계와는 수 ms 차이가 있을 수 있다.

## 항목별 판정

| 항목 / 기존 심각도 | Chromium | WebKit | 위치·근거 | 제안 / 규모 |
|---|---|---|---|---|
| F1 높음: 최종 수정 승인값으로 업무 차단 | 해결 | 해결 | review/service.py:180–191, 실제 정보 부족→가능 업무 진행 성공 / 가능→조건부 가능 disabled 및 HTTP 409 | 양방향 회귀 유지 / S |
| F2 중간: 정책 입력 덮어쓰기 | 해결 | 값 보존 해결; 클릭 측정 주의 | Policy.tsx:32–61. 최초 3/3씩 1.5 전송·검증 오류·입력 보존. 추가 WebKit 전송된 요청도 모두 1.5; 아래 자동화 한계 | dirty/snapshot 회귀 유지 / S |
| F3 중간: 전체 로딩 대기 | 해결 | 해결 | Monitoring.tsx:31–65. 제목·필터 190–330ms, 영역 독립 표시, 아래 6회 전체 수치 | 실제 데이터 증가 시 집계 시간 추적 / S |
| F4 중간: 다른 탭 신규 목록 정체 | 해결 | 해결 | Main.tsx:19,67–72. B 목록 2.5초 안정 후 A 요청 생성, reload 없이 신규 ID 확인 | tenant 목록 이벤트 회귀 유지 / S |
| F5 낮음: 잠정→최종 위치 이동 | 부분 미해결 | 부분 미해결 | Main.tsx:178 / ProgressivePanel.tsx:48–50. 요약 top 유지, 판단 top +2px, 업무 top +108/+114px | 불확실 판단 안내 슬롯도 동일 높이로 예약 / S |
| F6 낮음: 평가·정책 내부 키 노출 | 핵심 해결 | 핵심 해결 | Evaluation.tsx:57–59, labels.ts:116–128, Policy.tsx:90. 한국어 필드명·설명·의견 불일치 상태, 내부 키는 접힌 기술 상세 | 해당 라벨 회귀 유지 / S |

F6는 모든 영문을 제거했다는 뜻이 아니다. 브랜드·역할 labeler·“rules 필드” 안내 등은 남지만 P7의 `consensus_required`, `ai_need`, `team_set` 및 정책 snake_case 필드명 노출은 한국어 라벨로 바뀌었다. 평가 화면의 실제 불일치를 만들고 두 엔진에서 “검토자 간 의견 불일치 — 합의가 필요합니다”를 확인했으며 reviewer의 기존 라벨 값은 API 200으로 복원했다.

## F1 양방향 증거

| 브라우저 | request / review / task | 원안→최종 | 결과 |
|---|---|---|---|
| chromium | `req_71021fb87e3c46acad550a082cf968a7` / `rvw_be76d4c2150c4f6e842b6034253b3496` / `task_73ba59c110a64cbc979952543d27b13b` | 정보 부족→가능 | 대기→진행 UI 성공, feasibility 차단 없음 |
| chromium | `req_e3324b126fee4d84a4d80b3df639329e` / `rvw_56d9cede60b74b25a93d96478a7f7e2e` / `task_f275801fe6df4ec18bc88b0066e37cc9` | 가능→조건부 가능 | `feasibility_unresolved`, 진행 disabled, 직접 POST도 409 |
| webkit | `req_73f523e9d5b84a5dadfa55a228e7f175` / `rvw_2961c3dc6cc54fcf82b51fd60d6678d4` / `task_a17c0191f4a8404480b43f366db927a2` | 정보 부족→가능 | 대기→진행 UI 성공, feasibility 차단 없음 |
| webkit | `req_d4f156235a61462183175b300be070bc` / `rvw_68d1d3adcf094c7caad5b93cc8188615` / `task_94815fe555e246ad9bdffa335f009f79` | 가능→조건부 가능 | `feasibility_unresolved`, 진행 disabled, 직접 POST도 409 |

[Chromium 시작 성공](P8-chromium-F1-allow.png) · [차단 유지](P8-chromium-F1-block.png) · [WebKit 시작 성공](P8-webkit-F1-allow.png) · [차단 유지](P8-webkit-F1-block.png). 해당 표본은 선행 업무 없는 실제 일반 기술 업무이며 DB task를 강제로 수정하지 않았다.

## F3 콜드 진입 (ms)

각 영역의 셸은 제목/필터와 함께 표시된다. 아래 영역 값은 데이터 응답 반영 완료이며, “미수집/미검증”도 정상 응답의 유효 표시로 계산했다. 6회 모두 pending 0, 화면 오류 없이 종료했다.

| 엔진/회 | 제목 | 필터 | 핵심 지표 | SLO | 시스템 지연 | 사람 대기 | 실패/Trace | 알림 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| chromium/1 | 236.8 | 236.8 | 2520.9 | 2535.9 | 2520.9 | 2520.9 | 2520.9 | 287.2 |
| chromium/2 | 201.9 | 201.9 | 1640.7 | 1306.8 | 1640.7 | 1640.7 | 1306.8 | 1296.5 |
| chromium/3 | 190.5 | 190.5 | 2609.9 | 2597.9 | 2609.9 | 2609.9 | 2591.2 | 221.2 |
| webkit/1 | 330 | 330 | 2840 | 1380 | 2840 | 2840 | 1380 | 1380 |
| webkit/2 | 316 | 316 | 1649 | 1398 | 1649 | 1649 | 1383 | 1383 |
| webkit/3 | 316 | 316 | 2788 | 2788 | 2788 | 2788 | 2788 | 361 |

P7 WebKit 제목 7,795/7,824/8,840ms → P8 330/316/316ms. P8 전체 영역 완료도 2,840/1,649/2,788ms로 개선됐다. Chromium 제목은 P7 2,247/4,678/3,676ms → 236.8/201.9/190.5ms. 누적 데이터와 시스템 부하가 동일하지 않아 순수 코드 개선율로 단정하지 않는다. [Chromium 모니터링](P8-chromium-monitoring-1.png) · [WebKit 모니터링](P8-webkit-monitoring-1.png).

## 체감 속도 / F4 / F5

표본 문장: 회의실 예약 조회, 사내 공지 키워드 검색, 고객 문의 자동 분류, 시설 점검 입력·확인, 재고 수량 조회. 엔진별 텍스트 5건, 요청 번호만 추가. 10/10 잠정 및 최종 결과가 모두 관측됐다. p50은 nearest-rank 3번째 값이다.

| 엔진 | 잠정 p50 ms (P7) | 최종 p50 ms (P7) | 판정 |
|---|---:|---:|---|
| Chromium | 644.7 (608.5) | 1365.8 (1534.5) | 잠정 +5.9%, 최종 -11.0% |
| WebKit | 590.0 (492.0) | 1291.0 (1590.0) | 잠정 +19.9%, 최종 -18.8% |

최종 체감 속도 악화는 이 표본에서 없었다. 잠정 p50은 증가했으므로 “전 단계 무회귀”로 판정하지 않는다. P7은 n=10이며 요청 문장/모델 응답/실행 부하가 달라 유의한 성능 회귀인지 **불확실**하다.

| 엔진/# | request_id | 클릭→잠정 ms | 클릭→최종 ms |
|---|---|---:|---:|
| chromium/1 | `req_71021fb87e3c46acad550a082cf968a7` | 840.1 | 1517.6 |
| chromium/2 | `req_239ad24779114115996600db0adc9092` | 517.8 | 1213.6 |
| chromium/3 | `req_4e050d52bb684a71b1eefc053267615e` | 664.6 | 1365.8 |
| chromium/4 | `req_fa1b74c04bcb4066ade85a1dfe869c22` | 644.7 | 1383.6 |
| chromium/5 | `req_796b815dca214710883635a5c1613bbe` | 641.1 | 1302.4 |
| webkit/1 | `req_73f523e9d5b84a5dadfa55a228e7f175` | 813.0 | 1346.0 |
| webkit/2 | `req_6926a42e158c4f6f95a64fd1ec3d8d5a` | 696.0 | 1180.0 |
| webkit/3 | `req_c952d16138cb42b5b886f3f657b45748` | 582.0 | 1313.0 |
| webkit/4 | `req_edfe5039b8bc4bbf87f5f185bf1030e9` | 590.0 | 1291.0 |
| webkit/5 | `req_f201c4d046024ae7bfe9fe90aa2967c3` | 472.0 | 1231.0 |

F4는 각 엔진 첫 표본을 A에서 만들고, 선택 요청 없는 B에서 확인했다. A 최종 후 500ms 관측 대기 뒤 B locator는 Chromium 5ms / WebKit 9ms 만에 완료됐다(새 요청 발견 정확한 시각이 아니라 확인 상한 약 2.1초/1.9초). [Chromium B](P8-chromium-other-tab.png) · [WebKit B](P8-webkit-other-tab.png). 이번 P8은 한 API 인스턴스의 두 탭이며 P7의 다중 API/Redis 장애 시험은 반복하지 않았다.

### F5 잔여 — [심각도 낮음]

**위치:** `frontend/src/pages/main/ProgressivePanel.tsx:48–50`, `frontend/src/pages/Main.tsx:178`, `frontend/src/pages/main/main.css:14`.

**문제:** 요약 자리는 유지하지만 정보 부족/판단 보류 안내가 최종에서 새로 생겨 두 번째 판단 행과 업무 분담이 아래로 이동한다. 잠정 단계는 높은 신뢰도 숫자만 보이고 정보 부족 값의 별도 안내 슬롯이 없다.

**근거:** 모든 속도 표본에서 요약 top 변화 0px, 판단 grid top +2px, 업무 top Chromium +108px / WebKit +114px. 별도 스크롤 화면 재현도 동일: Chromium `req_bcfbcaaf7eb645faadabd680406fae0e`, WebKit `req_bd4b150a3ce6405197205b633a0d8f5b`. 판단 grid 높이는 잠정 388px → 최종 494px/500px. Chromium `hadRecentInput=false` layout-shift 합은 각 표본 0.00002491로 P7 0.01349–0.03348보다 작지만, 최초 viewport 아래의 이동을 충분히 반영하지 않는다. WebKit은 layout-shift API 미지원이므로 0으로 해석하지 않는다.

[Chromium 잠정](P8-chromium-provisional.png) → [최종](P8-chromium-final-layout.png), [WebKit 잠정](P8-webkit-provisional.png) → [최종](P8-webkit-final-layout.png).

**제안 수정:** 이미 알려진 잠정 분류가 정보 부족/판단 보류이면 최종과 같은 불확실성 안내를 렌더링하고 같은 공간을 유지한다. 최종 근거 행/신뢰 신호를 고려한 판단 카드 최소 높이를 맞춘다. `layout-shift<0.005`만 검사하지 말고 스크롤된 상태에서 summary/judgment/tasks의 document top 차이도 검증한다. **예상 규모: S.**

## F2 자동화 관찰 한계 — [심각도 낮음, 불확실]

**위치:** WebKit `/policy` 새 세션의 첫 입력 직후 “서버 검증”으로 자동 스크롤·클릭.

**문제/근거:** 최초 실행 2회 중 1회 클릭 후 요청 없음으로 30초 대기 종료. 재실행 3/3은 정상이며, 추가 5회 중 1회·이벤트 추적 8회 중 1회 같은 무요청 관찰. 값은 계속 `{"ai_need":1.5}`로 보존됐다. 추적 실패에서는 pointerdown 대상이 SECTION, pointerup이 BUTTON, click이 SECTION이었다(x=353,y=549, scrollY=2297); 따라서 React 검증 버튼에 실제 click이 전달되지 않았다. 같은 화면 재클릭은 정상 전송·검증 오류. 입력 덮어쓰기/잘못된 valid=true는 한 번도 재현되지 않았다.

**제안:** 자동화에서 버튼까지 스크롤한 뒤 위치가 안정된 것을 확인하고 클릭해 재검증한다. 물리 WebKit/Safari에서도 발생하면 정책 액션을 고정 영역에 두고 초기 높이 변화를 줄인다. 자동 스크롤 드라이버와 앱 레이아웃 중 책임 소재가 **불확실**하여 확정 신규 제품 결함으로 집계하지 않는다. **예상 규모: S(재현 분리).**

[정책 입력 및 오류](P8-webkit-policy.png) · [한국어 정책](P8-chromium-policy-labels.png) · [Chromium 의견 불일치](P8-chromium-disagreement.png) · [WebKit 의견 불일치](P8-webkit-disagreement.png).

## 정리

합성 요청·승인·전이 감사 기록은 남긴다. 정책 게시/되돌리기는 하지 않았고 활성 v30 설정을 변경하지 않았다. 평가 reviewer의 라벨 값은 각 임시 불일치 시험 전 값으로 복원했으며 변경·복원 이력은 남는다. 실행 임시 harness/로그/캐시는 최종 산출물이 아니며, 제품 변경 없이 이 보고서와 P8 PNG만 산출한다.

완료 확인: P8 소유 API8991·Vite6291·worker·collector·watchdog 종료 및 두 포트 listener 없음. 모든 정상 종료 harness의 Playwright 브라우저를 닫았고, 실패 harness도 종료됐다. 공유 Neo4j/Redis는 running healthy, Redis PING=PONG. git tracked diff 없음. 임시 harness·로그·캐시는 제거했다.
