# T38-R 확장 연결 시나리오 재실행 — X01–X10 최종 판정

이전 실행: `artifacts/validation/20261003T093618Z/extension/scenario-evidence.md`(X01–X10 통과, 한계 F3–F9). 이 보고는 FIX-S/O/C/E/SSE/R 이후 최신 코드로 새 tenant에서 다시 실행한 결과다(이전 증거는 덮어쓰지 않음).

- 실행 tenant: `t-x38r-10031227` (전용, worker는 `--tenant` 제한), 결과 디렉터리: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/20261003T122747Z/extension`
- Jev: `JEV_MODE=live` (실제 모델 호출, 모든 판단 `mode=live`). 저장소: 공유 Neo4j(정지하지 않음). 데이터 디렉터리(journal/원본 파일)는 이 작업 전용 경로.
- 이 보고는 **확장 게이트 X01–X10**만 판정한다. 기존 게이트(G01–G12)는 4절 'X10 회귀'의 '기존 게이트 별도 보고' 표에서 재실행 결과로만 다루며, G 판정 자체는 T27 소관이다.

## 1. 판정 요약

| 게이트 | 판정 | 근거 요약 |
| --- | --- | --- |
| X01 | **통과** | API/DB 검사 4건 통과, 브라우저 검사 1건 통과 |
| X02 | **통과** | API/DB 검사 5건 통과, 브라우저 검사 2건 통과 |
| X03 | **통과** | API/DB 검사 9건 통과, 브라우저 검사 4건 통과 |
| X04 | **통과** | API/DB 검사 8건 통과, 브라우저 검사 2건 통과 |
| X05 | **통과** | API/DB 검사 5건 통과, 브라우저 검사 4건 통과 |
| X06 | **통과** | API/DB 검사 9건 통과, 브라우저 검사 6건 통과 |
| X07 | **통과** | API/DB 검사 4건 통과, 브라우저 검사 4건 통과 |
| X08 | **통과** | API/DB 검사 3건 통과, 브라우저 검사 7건 통과 |
| X09 | **통과** | API/DB 검사 2건 통과, 브라우저 검사 2건 통과 |
| X10 | **통과** | make test 백엔드 136 통과·1 건너뜀(live 전용)+vitest 37 통과, make test-fault 11/11, make test-acceptance 백엔드 40/40·UI 12/12, 확장 게이트 pytest 9/9 |
| F3 Trace 규칙 적용 단계 상세 | **통과** | API/DB 검사 1건 통과, 브라우저 검사 1건 통과 |
| F4 불변 조건 허용 목록·blocked_by_invariant | **통과** | API/DB 검사 4건 통과, 브라우저 검사 1건 통과 |
| F5 자료 부족 승인 확인 | **통과** | API/DB 검사 5건 통과, 브라우저 검사 1건 통과 |
| F6 섀도 Run id 분리 | **통과** | API/DB 검사 1건 통과, 브라우저 검사 1건 통과 |
| F7 시각 직렬화(Flow/단계 상세) | **통과** | API/DB 검사 1건 통과, 브라우저 검사 0건 통과 |
| 근거 계층(텍스트 전용 요청의 chat EvidenceSpan) | **통과** | API/DB 검사 3건 통과, 브라우저 검사 1건 통과 |

## 2. 10단계 실제 ID 표

| 단계 | 항목 | 실제 ID / 값 |
| --- | --- | --- |
| 1 | 접수·판단 요청(8건, AI 원안 ai_need=`불필요`) | `req_3dc8f5415b7c4804aede76f9b9e7e187`, `req_52d6c424653d4808947ab85ffb7550b8`, `req_2744ff85abff43d18524b8fbff205485`, `req_e13745e1a3324d48812e6baef41f3ada`, `req_0b2ee90b9862459694a714133217bf73`, `req_31aeb1815a934213b2021a8a332e223c`, `req_b94acf8a7799418e83ed3ce36b33e30b`, `req_e5a4b6149b7a4a468bc95b086a2bfd7e` |
| 1 | 같은 방향 수정 3건(→`필요`) | `req_e5a4b6149b7a4a468bc95b086a2bfd7e`→`cor_e1c531571fd64851b38fb3f407ad7ff9`, `req_b94acf8a7799418e83ed3ce36b33e30b`→`cor_a12d0808c0124f07baf6b7d73b7663b8`, `req_31aeb1815a934213b2021a8a332e223c`→`cor_e4a28aea4e6c4d4880eb64292314cdc1` |
| 1 | 반례 1건(수정 없이 승인) | `req_0b2ee90b9862459694a714133217bf73` |
| 1 | 다른 방향 수정 2건(→`혼합`) | `req_e13745e1a3324d48812e6baef41f3ada`→`cor_f0817ad4222842cf9d759be1a3e4e647`, `req_2744ff85abff43d18524b8fbff205485`→`cor_58af725183634ae9aeaa16b373a5f990` |
| 3 | 후보(지지 3, 제안) / 후보(지지 2, 자료 부족) | `cand_8fcc507094e6868374ddec5c` / `cand_e123faef72028b6d12635bef` |
| 4 | 범위 수정 승인 결정 / 규칙 버전 / 기반 Config | `rdec_f01ba658005b4be0bbc4f24cb8accb2f` / `R-AI_NEED-01@1` / v1 |
| 5 | 섀도 검증 / 게시 Config | `val_ae2b8a074e3d412aa003c57a6efab5d4` / v2 |
| 6 | 범위 내 새 요청(사용) | `req_b7638d574aa7420e8c8e632e206247d8` run `run_2c5c765f9cbc4211b33f06e883bd0552` step `step_30e7c2a911fc40f58ba3238032ba45b0` 불필요→필요 |
| 6 | 범위 내 새 요청(사용) | `req_ce5ec4dbc4614a1ebb1e72c2b5e9aaff` run `run_4711fecab95a4d4e9ab4b4d7862c7e73` step `step_1c25f6f5e6c841c1ad9837be8e8b555b` 불필요→필요 |
| 6 | 범위 내 새 요청(사용) | `req_37be29fc5ba64774855602dc6604fb3e` run `run_d97a42f321e4486489579ed167f27c00` step `step_36320b9b1a0f4b5d8943692df49d3e88` 불필요→필요 |
| 6 | 범위 밖 새 요청(미사용 기록) | `req_6b09736cb81f40eb96a451f595f44c66` run `run_ca70aafc128d4634b4518075ee66995c` step `step_3a8e4c6e9bc94cc58250723621fe7d75` 불필요 유지 |
| 7a | lead_org 수정 경로: 후보/결정/버전/Config (`IT팀`→`현업`) | `cand_9a49449bb55ab51162c213e0` / `rdec_16b2b896cc344614b98c2423db381d52` / `R-LEAD_ORG-01@1` / v3 · 수정 `cor_503b976a073f4aef9f95a2f9474ca09b`, `cor_382a770a59a5438682cf9d5a21d0a74d`, `cor_a2f1d4fe9a4c4f919deefe62082320a3` · 검증 `val_e8697532f8bc4b8cabcee5205d372aba`(섀도 Run `run_shadow_1335947c489b4ab297ef717994dc285b`) · 새 요청 `req_1b06d22ddfbd4c26b4dfeef6ebfa2eb6` run `run_37c1373717254589994b666d8dc5f0d9` IT팀→현업 |
| F4 | DB 직접 삽입 위반 규칙 적용 | tenant `t-x38r-10031227i` Config v2 규칙 `R-URGENCY-91@1`, `R-FEASIBILITY-92@1` · 요청 `req_c89f7bb6abf549efbee8e901316c260c` run `run_30b0b4829e9047b9adb4d6136b3d1e09` step `step_34a8e70ab52e4436bfd0166122c6d5d1` |
| F5 | 자료 부족 후보 승인(API) / 화면 승인 대상 | 후보 `cand_e123faef72028b6d12635bef` 결정 `rdec_86485b0355534353b4d3a4aec8ade3c1` 버전 `R-AI_NEED-02@1` / 후보 `cand_0c4749cc88828c487a3d8ead` |
| 7 | 근거 있는 규칙(feasibility `정보 부족`→`조건부 가능`, 텍스트 전용 요청) 후보/결정/버전/Config | `cand_79f6d9ca44e33854681ab0b0` / `rdec_65ada79162344602b90a1ae72c736684` / `R-FEASIBILITY-01@1` / v4 |
| 7 | 역추적 사슬 | step `step_a4920d1256274c3db4d14c561ed044d4` → `R-FEASIBILITY-01@1` → `rdec_65ada79162344602b90a1ae72c736684` → `cand_79f6d9ca44e33854681ab0b0` → `cor_88104cfdf04742de93884ec0aa95a41f` → `mout_b896ac7666e045a297e3424e1a3654c9` → `esp_00bcd34b6147453d9ce1aa6d1bfde782` |
| 8 | 중단/ v2 게시 / 되돌리기 Config | v5 / v6 / v7 (v2=`R-AI_NEED-01@2`) |
| 8 | 진행 중 / 중단 후 / v2 / 되돌린 뒤 요청 | `req_4f64895718614271894b4fb1193202ff` / `req_86170fbfe48e4a668f38914f738360d4` / `req_ffb17c16c9b545beb734728696da558a` / `req_e69c48ef3dfa45c88198a8451420164c` |
| 9 | 재시작 후 새 요청 | `req_01626ab5ff9e4a64bd4620528eaf53dd` run `run_ca76571f8f02467bb1f80045c8299d93` |

## 3. 게이트별 증거 (최신 결과 + 재시험 이력)

### X01 — 통과

- [통과] review decisions submitted
  - 증거: `{"plan": {"same_direction": ["req_e5a4b6149b7a4a468bc95b086a2bfd7e", "req_b94acf8a7799418e83ed3ce36b33e30b", "req_31aeb1815a934213b2021a8a332e223c"], "counter": "req_0b2ee90b9862459694a714133217bf73", "other_direction": ["req_e13745e1a3324d48812e6baef41f3ada", "req_2744ff85abff43d18524b8fbff205485"]}, "original": "불필요", "dir_y": "필요", "dir_z": "혼합"}`
- [통과] DB Correction == API(/requests/{id}/corrections, /learning/corrections); AI original kept; CORRECTS->ModelOutput
  - 증거: `{"corrections": {"req_e5a4b6149b7a4a468bc95b086a2bfd7e": {"correction_id": "cor_e1c531571fd64851b38fb3f407ad7ff9", "review_id": "rvw_0e3194df0bf843c98f0f08d9f365d65c", "run_id": "run_b3e6a3027d744d8e972f0a999631de78", "revision_id": "rev_ba6b067b935e4d9ca046462ad2336852", "config_version": 1, "ai_value": "\"불필요\"", "corrected_value": "\"필요\"", "corrected_by": "usr_t-x38r-10031227_reviewer", "corrected_at": "2026-10-03T12:28:32.313000000+00:00", "reason": "T38: ai_need 같은 방향 수정", "evidence_span_ids": [], "checks": {"id": true, "ai_value": true, "corrected_value": true, "reason": true, "corrected_by": true, "corrected_at": true, "revision_id": true, "run_id": true, "config_version": true, "lis…`
- [**실패**] lead_org corrections (text-only requests) keep evidence span IDs: Correction.evidence_span_ids == CITES targets of the corrected ModelOutput; spans are chat sentences — _재시험으로 대체: wrong expectation: the live model cites no span for lead_org; retested as '(retest) lead_org corrections …'_
  - 증거: `{"original_lead_org": "IT팀", "target": "현업", "corrections": {"cor_503b976a073f4aef9f95a2f9474ca09b": {"request": "req_44f8f9b084594f8187684e9781f642fb", "spans": []}, "cor_382a770a59a5438682cf9d5a21d0a74d": {"request": "req_f893e67063944583806ba8391bee4914", "spans": []}, "cor_a2f1d4fe9a4c4f919deefe62082320a3": {"request": "req_bef8e1a8aa97464aaf1dcb1d0586db4e", "spans": []}}, "span_sources": []}`
- [통과] (retest) lead_org corrections: Correction.evidence_span_ids == CITES targets of the corrected ModelOutput (both empty: Jev cites no span for lead_org)
  - 증거: `{"corrections": {"cor_503b976a073f4aef9f95a2f9474ca09b": {"request": "req_44f8f9b084594f8187684e9781f642fb", "spans": [], "cites": []}, "cor_382a770a59a5438682cf9d5a21d0a74d": {"request": "req_f893e67063944583806ba8391bee4914", "spans": [], "cites": []}, "cor_a2f1d4fe9a4c4f919deefe62082320a3": {"request": "req_bef8e1a8aa97464aaf1dcb1d0586db4e", "spans": [], "cites": []}}}`
- [통과] feasibility corrections (feas, text-only requests): Correction.evidence_span_ids == CITES targets of the corrected ModelOutput; every correction has chat-sentence spans
  - 증거: `{"original": "정보 부족", "target": "조건부 가능", "corrections": {"cor_f3c482e76e094ce5825c7264717b5d06": {"request": "req_7c3fde8d66cb4f708cd0112299129235", "spans": ["esp_df1e8a54e1a5433a9b2c4e038e56e845"]}, "cor_f53eaee7e65f4d4a97866d464f631bec": {"request": "req_1af31c93fd864e398be8734a8e0787c8", "spans": ["esp_5406be984af944e2b3032d16c1f079fe"]}, "cor_88104cfdf04742de93884ec0aa95a41f": {"request": "req_be8192ae007e4a7c92089b38c3aef6ea", "spans": ["esp_00bcd34b6147453d9ce1aa6d1bfde782"]}}, "span_sources": [{"id": "esp_00bcd34b6147453d9ce1aa6d1bfde782", "source": "chat"}, {"id": "esp_5406be984af944e2b3032d16c1f079fe", "source": "chat"}, {"id": "esp_df1e8a54e1a5433a9b2c4e038e56e845", "source": "ch…`
- [브라우저 ui1: **failed**] [X01][X02] reviewer sees AI original vs correction with who/when/revision/run/Config, support & counter examples, 자료 부족 — Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed
  - 화면 값: `[{"candidate": "cand_8fcc507094e6868374ddec5c", "support_rows": [{"request": "req_e5a4b6149b7a4a468bc95b086a2bfd7e", "correction": "cor_e1c531571fd64851b38fb3f407ad7ff9", "run": "run_b3e6a3027d744d8e972f0a999631de78", "revision": "rev_ba6b067b935e4d9ca046462ad2336852", "config": 1}, {"request": "req_b94acf8a7799418e83ed3ce36b33e30b", "correction": "cor_a12d0808c0124f07baf6b7d73b7663b8", "run": "run_f9904b08f4ad46aeb19f3c3f61d73c1b", "revision": "rev_254e80318d894c0291d70bed85eb9ab0", "config": 1…`
- [브라우저 ui1: 통과] [X01][X02] reviewer sees AI original vs correction with who/when/revision/run/Config, support & counter examples, 자료 부족
  - 화면 값: `[{"candidate": "cand_8fcc507094e6868374ddec5c", "support_rows": [{"request": "req_e5a4b6149b7a4a468bc95b086a2bfd7e", "correction": "cor_e1c531571fd64851b38fb3f407ad7ff9", "run": "run_b3e6a3027d744d8e972f0a999631de78", "revision": "rev_ba6b067b935e4d9ca046462ad2336852", "config": 1}, {"request": "req_b94acf8a7799418e83ed3ce36b33e30b", "correction": "cor_a12d0808c0124f07baf6b7d73b7663b8", "run": "run_f9904b08f4ad46aeb19f3c3f61d73c1b", "revision": "rev_254e80318d894c0291d70bed85eb9ab0", "config": 1…`

### X02 — 통과

- [통과] candidate (3 same direction) linked to Correction IDs with counter/scope/uncertainty
  - 증거: `{"generate_status": 200, "candidate": {"id": "cand_8fcc507094e6868374ddec5c", "field": "ai_need", "status": "제안", "support_ids": ["cor_a12d0808c0124f07baf6b7d73b7663b8", "cor_e1c531571fd64851b38fb3f407ad7ff9", "cor_e4a28aea4e6c4d4880eb64292314cdc1"], "counter_ids": ["rdec_2a438b8572a843b1ac79745b7a27e559", "rdec_631ea52db0da4ace8c86c03d503d984e", "rdec_63e79ba5a7ee49a5a49a024eede69a88"], "api_support_ids": ["cor_a12d0808c0124f07baf6b7d73b7663b8", "cor_e1c531571fd64851b38fb3f407ad7ff9", "cor_e4a28aea4e6c4d4880eb64292314cdc1"], "scope": {"all": [{"field": "ai_need", "op": "eq", "value": "불필요"}, {"field": "feasibility", "op": "eq", "value": "정보 부족"}, {"field": "lead_org", "op": "eq", "value": "…`
- [통과] other direction with 2 corrections is '자료 부족' (DB==API)
  - 증거: `{"candidate": {"id": "cand_e123faef72028b6d12635bef", "field": "ai_need", "status": "자료 부족", "support_ids": ["cor_58af725183634ae9aeaa16b373a5f990", "cor_f0817ad4222842cf9d759be1a3e4e647"], "counter_ids": ["rdec_02aa1223828b43a59b9c06e5c82f787d", "rdec_2a438b8572a843b1ac79745b7a27e559", "rdec_40c1dad28a67463891676cfb8db7c9c2", "rdec_f92a47759ade4ea9a683e537655d0b69"], "api_support_ids": ["cor_58af725183634ae9aeaa16b373a5f990", "cor_f0817ad4222842cf9d759be1a3e4e647"], "scope": {"all": [{"field": "ai_need", "op": "eq", "value": "불필요"}, {"field": "feasibility", "op": "eq", "value": "정보 부족"}, {"field": "lead_org", "op": "eq", "value": "IT팀"}, {"op": "lte", "signal": "ai_team_involvement", "value…`
- [통과] candidate generation did not change Config
  - 증거: `{"config_version": 1}`
- [통과] lead_org candidate: support == the 3 Correction IDs, status 제안, scope/uncertainty present
  - 증거: `{"candidate": "cand_9a49449bb55ab51162c213e0", "status": "제안", "action": {"set": "현업"}, "support": ["cor_382a770a59a5438682cf9d5a21d0a74d", "cor_503b976a073f4aef9f95a2f9474ca09b", "cor_a2f1d4fe9a4c4f919deefe62082320a3"], "counter_count": 3, "scope": {"all": [{"field": "ai_need", "op": "eq", "value": "혼합"}, {"field": "feasibility", "op": "eq", "value": "정보 부족"}, {"field": "lead_org", "op": "eq", "value": "IT팀"}, {"op": "lte", "signal": "ai_team_involvement", "value": 0.5}, {"op": "gte", "signal": "business_involvement", "value": 0.5}, {"op": "gte", "signal": "clinical_safety", "value": 0.5}, {"op": "gte", "signal": "it_team_involvement", "value": 0.5}, {"op": "gte", "signal": "pharmacovigilan…`
- [통과] feasibility candidate: support == the 3 Correction IDs, status 제안, scope/uncertainty present, action = set 조건부 가능
  - 증거: `{"candidate": "cand_79f6d9ca44e33854681ab0b0", "status": "제안", "action": {"set": "조건부 가능"}, "support": ["cor_88104cfdf04742de93884ec0aa95a41f", "cor_f3c482e76e094ce5825c7264717b5d06", "cor_f53eaee7e65f4d4a97866d464f631bec"], "counter_count": 3, "scope": {"all": [{"field": "ai_need", "op": "eq", "value": "필요"}, {"field": "feasibility", "op": "eq", "value": "정보 부족"}, {"field": "lead_org", "op": "eq", "value": "IT팀"}, {"op": "lte", "signal": "ai_team_involvement", "value": 0.5}, {"op": "gte", "signal": "business_involvement", "value": 0.5}, {"op": "lte", "signal": "clinical_safety", "value": 0.5}, {"op": "gte", "signal": "it_team_involvement", "value": 0.5}, {"op": "lte", "signal": "pharmacovig…`
- [브라우저 ui1: **failed**] [X01][X02] reviewer sees AI original vs correction with who/when/revision/run/Config, support & counter examples, 자료 부족 — Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed
  - 화면 값: `[{"candidate": "cand_8fcc507094e6868374ddec5c", "support_rows": [{"request": "req_e5a4b6149b7a4a468bc95b086a2bfd7e", "correction": "cor_e1c531571fd64851b38fb3f407ad7ff9", "run": "run_b3e6a3027d744d8e972f0a999631de78", "revision": "rev_ba6b067b935e4d9ca046462ad2336852", "config": 1}, {"request": "req_b94acf8a7799418e83ed3ce36b33e30b", "correction": "cor_a12d0808c0124f07baf6b7d73b7663b8", "run": "run_f9904b08f4ad46aeb19f3c3f61d73c1b", "revision": "rev_254e80318d894c0291d70bed85eb9ab0", "config": 1…`
- [브라우저 r1: 통과] [X02][X05] lead_org rule on the learning screen: candidate → decision → version → shadow validation → published, application count = stored APPLIED
  - 화면 값: `[{"rule": "R-LEAD_ORG-01@1", "action": {"set": "현업"}, "applications": 14, "validation": "val_e8697532f8bc4b8cabcee5205d372aba"}]`
- [브라우저 ui1: 통과] [X01][X02] reviewer sees AI original vs correction with who/when/revision/run/Config, support & counter examples, 자료 부족
  - 화면 값: `[{"candidate": "cand_8fcc507094e6868374ddec5c", "support_rows": [{"request": "req_e5a4b6149b7a4a468bc95b086a2bfd7e", "correction": "cor_e1c531571fd64851b38fb3f407ad7ff9", "run": "run_b3e6a3027d744d8e972f0a999631de78", "revision": "rev_ba6b067b935e4d9ca046462ad2336852", "config": 1}, {"request": "req_b94acf8a7799418e83ed3ce36b33e30b", "correction": "cor_a12d0808c0124f07baf6b7d73b7663b8", "run": "run_f9904b08f4ad46aeb19f3c3f61d73c1b", "revision": "rev_254e80318d894c0291d70bed85eb9ab0", "config": 1…`

### X03 — 통과

- [통과] all non-rule_admin roles get 403 on decision/scope-change/reject/version/validate/mark-validated/publish/stop/revert
  - 증거: `{"status_by_role": {"requester": {"decision": 403, "decision_scope_change": 403, "reject": 403, "create_version": 403, "validate": 403, "mark_validated": 403, "publish": 403, "stop": 403, "revert": 403}, "reviewer": {"decision": 403, "decision_scope_change": 403, "reject": 403, "create_version": 403, "validate": 403, "mark_validated": 403, "publish": 403, "stop": 403, "revert": 403}, "team_member": {"decision": 403, "decision_scope_change": 403, "reject": 403, "create_version": 403, "validate": 403, "mark_validated": 403, "publish": 403, "stop": 403, "revert": 403}, "operator": {"decision": 403, "decision_scope_change": 403, "reject": 403, "create_version": 403, "validate": 403, "mark_valida…`
- [통과] policy_editor cannot publish a rules diff via /api/policy/publish
  - 증거: `{"status": 422, "body": "{\"detail\":{\"code\":\"RULE_ADMIN_REQUIRED\",\"reason\":\"rules 변경은 rule_admin 전용 경로에서만 허용됩니다.\"}}"}`
- [통과] rejected calls left candidate/decision/version/config state unchanged
  - 증거: `{"before": {"RuleCandidate": {"count": 2, "sha256": "f7d41f43d05be529"}, "RuleDecision": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "RuleVersion": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "ConfigVersion": {"count": 1, "sha256": "fa2ca75ce47e9eec"}}, "after": {"RuleCandidate": {"count": 2, "sha256": "f7d41f43d05be529"}, "RuleDecision": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "RuleVersion": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "ConfigVersion": {"count": 1, "sha256": "fa2ca75ce47e9eec"}}}`
- [통과] single review approval (API) changed no RuleCandidate/RuleDecision/RuleVersion/ConfigVersion
  - 증거: `{"review_id": "rvw_9243de34868b452c98e10e4adc4d303d", "request_id": "req_3dc8f5415b7c4804aede76f9b9e7e187", "state": {"RuleCandidate": {"count": 2, "sha256": "f7d41f43d05be529"}, "RuleDecision": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "RuleVersion": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "ConfigVersion": {"count": 1, "sha256": "fa2ca75ce47e9eec"}}, "active_config": 1}`
- [통과] policy_editor cannot publish a rules diff via /api/policy/publish (retest with a valid rule id)
  - 증거: `{"status": 422, "body": "{\"detail\":{\"code\":\"RULE_ADMIN_REQUIRED\",\"reason\":\"rules 변경은 rule_admin 전용 경로에서만 허용됩니다.\"}}"}`
- [통과] rule_admin scope-change approval: confirmed scope stored (differs from proposal), candidate approved
  - 증거: `{"decision_id": "rdec_f01ba658005b4be0bbc4f24cb8accb2f", "confirmed_scope": {"all": [{"field": "ai_need", "op": "eq", "value": "불필요"}, {"field": "lead_org", "op": "eq", "value": "IT팀"}, {"op": "lte", "signal": "clinical_safety", "value": 0.5}, {"op": "lte", "signal": "regulatory", "value": 0.5}]}, "proposed_scope_predicates": 10, "db": {"action": "approve_with_scope_change", "by": "usr_t-x38r-10031227_rule_admin", "candidate_status": "approved"}}`
- [통과] publish before validation is refused (409) and Config version unchanged
  - 증거: `{"status": 409, "body": "{\"detail\":{\"code\":\"INVALID_TRANSITION\",\"reason\":\"게시 가능한 검증 상태가 아닙니다.\"}}", "active_config": 1}`
- [통과] validated rule published as new Config version (rule in active rules, PUBLISHED_IN), audit + rule.* events recorded
  - 증거: `{"config_version": 2, "prior": 1, "active_rules": ["R-AI_NEED-01@1"], "audit": {"RuleCandidate:cand_8fcc507094e6868374ddec5c": [["rule.decision", "usr_t-x38r-10031227_rule_admin", "T38: 범위를 임상·규제 신호 낮음으로 확정"]], "RuleVersion:R-AI_NEED-01@1": [["rule.version_created", "usr_t-x38r-10031227_rule_admin", "T38: 규칙 버전 생성"], ["rule.validated", "usr_t-x38r-10031227_rule_admin", "T38: 부작용 0건 확인"]], "ConfigVersion:2": [["rule.publish", "usr_t-x38r-10031227_rule_admin", "T38: 게시"]]}, "events": [{"kind": "rule.decision", "n": 1}, {"kind": "rule.publish", "n": 1}, {"kind": "rule.validated", "n": 1}, {"kind": "rule.version_created", "n": 1}]}`
- [통과] rule_admin rejects a candidate: decision+audit recorded, status rejected; approval after rejection and version creation refused; no RuleVersion/Config change
  - 증거: `{"candidate": "cand_c17cccefbccbc8ec2ba3f9c2", "reject": 200, "approve_after_reject": [409, "{\"detail\":{\"code\":\"CANDIDATE_REJECTED\",\"reason\":\"기각된 후보입니다.\"}}"], "create_version_after_reject": [409, "{\"detail\":{\"code\":\"CANDIDATE_REJECTED\",\"reason\":\"기각된 후보에서 규칙을 만들 수 없습니다.\"}}"], "db": [{"a": "reject", "by": "usr_t-x38r-10031227_rule_admin", "r": "T38: 근거 부족으로 기각", "s": "rejected"}], "audit": [["rule.decision", "usr_t-x38r-10031227_rule_admin", "T38: 근거 부족으로 기각"]]}`
- [브라우저 ui1: 통과] [X03] requester has no access to rule learning; no rule actions exposed
- [브라우저 ui1: 통과] [X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족
  - 화면 값: `[{"ui_used": 16, "ui_out": 8, "db": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0}, "after": {"sample_count": 24, "corrections": 6, "review_transitions": 24, "failures": 0, "classification_changes": 16}, "used": {"sample_count": 16, "corrections": 3, "review_transitions": 16, "failures": 0, "classification_changes": 16}, "out_of_scope": {"sample_count": 8, "corrections": 3, "review_transitions": 8, "failures": 0, "classificat…`
- [브라우저 ui1: 통과] [X03] requester has no access to rule learning; no rule actions exposed
- [브라우저 ui1: 통과] [X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족
  - 화면 값: `[{"ui_used": 16, "ui_out": 8, "db": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0}, "after": {"sample_count": 24, "corrections": 6, "review_transitions": 24, "failures": 0, "classification_changes": 16}, "used": {"sample_count": 16, "corrections": 3, "review_transitions": 16, "failures": 0, "classification_changes": 16}, "out_of_scope": {"sample_count": 8, "corrections": 3, "review_transitions": 8, "failures": 0, "classificat…`

### X04 — 통과

- [통과] protected nodes (Task/Assignment/Review/ReviewDecision/Event/Request/Judgment/Correction) identical before/after shadow
  - 증거: `{"before": {"Task": {"count": 7, "sha256": "f71a9c39197509e1"}, "Assignment": {"count": 7, "sha256": "c57064d76245a475"}, "Review": {"count": 8, "sha256": "bcbd649ffefa550e"}, "ReviewDecision": {"count": 7, "sha256": "9e69d59644bab7f9"}, "Event": {"count": 129, "sha256": "a114a4f812623660"}, "Request": {"count": 8, "sha256": "6897273ce444d8ed"}, "Judgment": {"count": 8, "sha256": "09f2ede64c8bf8a6"}, "Correction": {"count": 5, "sha256": "6f2398434d50c9d8"}}, "after": {"Task": {"count": 7, "sha256": "f71a9c39197509e1"}, "Assignment": {"count": 7, "sha256": "c57064d76245a475"}, "Review": {"count": 8, "sha256": "bcbd649ffefa550e"}, "ReviewDecision": {"count": 7, "sha256": "9e69d59644bab7f9"}, "…`
- [통과] counts and Request.active_run_id pointers identical before/after shadow
  - 증거: `{"before": {"Task": 7, "Assignment": 7, "Review": 8, "Event": 129, "Notification": 0, "ReviewDecision": 7, "Judgment": 8, "Request": 8, "active_run_pointers": {"n": 8, "ptr": ["req_0b2ee90b9862459694a714133217bf73=run_b86655052ae84b32a8e741e951a6b54e", "req_2744ff85abff43d18524b8fbff205485=run_9b2d04842f38492fbb92687b8dd98874", "req_31aeb1815a934213b2021a8a332e223c=run_ee52a1ccef9b42d4a31203c5f08e9eb2", "req_3dc8f5415b7c4804aede76f9b9e7e187=run_bfdfc2c144124be08abfa8c20f7a7aae", "req_52d6c424653d4808947ab85ffb7550b8=run_6f374fb67f8c4674b97d713284109350", "req_b94acf8a7799418e83ed3ce36b33e30b=run_f9904b08f4ad46aeb19f3c3f61d73c1b", "req_e13745e1a3324d48812e6baef41f3ada=run_ab12ee5450ad4e89b023…`
- [**실패**] monitoring SLO/summary denominators and alerts unchanged by shadow — _재시험으로 대체: first attempt was vacuous (collector stopped, clock-dependent window); retested with collector running_
  - 증거: `{"before": "7e8ffa57d6bac3b8", "after": "462c4711f207c27a", "summary_after": {"summary": {"availability": {"valid_calls": 8, "successful_calls": 8, "failed_calls": 0, "pending_calls": 0, "unknown_validity": 0, "ratio": 1.0}, "judgment": {"eligible_requests": 8, "within_120s": 8, "failed_120s": 0, "pending_120s": 0, "ratio": 1.0, "candidate_commits": 8, "failed_runs": 0, "late_recoveries": 0, "unconfirmed_samples": 0}, "latency_ms": {"intake_p95": 188.0, "text_first_p95": null, "attachment_first_p95": 15296.810000000001, "sse_deliver_p95": null, "revision_p95": 3692.0, "step_p95": 3306.0}, "requests": {"received": 8, "failed_before_id": 0}, "file_exclusions": 0, "first_eligible_after_file_dec…`
- [**실패**] ValidationRun (POST result == GET API == DB): conditions, sample counts, side_effects=0, run_kind=shadow — _재시험으로 대체: 같은 항목을 수정·재실행해 통과(시험 코드 정정 후, 아래 이력 참조)_
  - 증거: `{"validation_id": "val_ae2b8a074e3d412aa003c57a6efab5d4", "sample_count": 8, "labeled_count": 7, "changed_count": 8, "changes_by_value": {"ai_need:필요": 8}, "base": 1, "candidate": "1+R-AI_NEED-01@1", "human_correction_needed_base/candidate": [5, 4], "window": ["2026-01-01T00:00:00+00:00", "2026-12-31T00:00:00+00:00"], "shadow_run_kind": [], "field_equal": {"sample_count": true, "labeled_count": true, "changed_count": true, "side_effects": true, "status": true, "run_kind": true, "base_config_version": true, "candidate_config_version": true, "max_calls": true, "calls": true, "human_correction_needed_base": true, "human_correction_needed_candidate": true}}`
- [통과] lead_org rule validated by shadow: side_effects=0, completed, sample counts recorded, shadow Run id != ValidationRun id
  - 증거: `{"id": "val_e8697532f8bc4b8cabcee5205d372aba", "run_id": "run_shadow_1335947c489b4ab297ef717994dc285b", "sample_count": 18, "labeled_count": 13, "changed_count": 6, "side_effects": 0, "status": "completed", "calls": 0}`
- [통과] feasibility rule validated by shadow: side_effects=0, completed, sample counts recorded, shadow Run id != ValidationRun id
  - 증거: `{"id": "val_c9703714627f4b33862c115123f71ef8", "run_id": "run_shadow_f9db69bc78d746e9a6ca6b4fd3c1e7c0", "sample_count": 31, "labeled_count": 19, "changed_count": 20, "side_effects": 0, "status": "completed", "calls": 0}`
- [통과] (retest 2: shadow-only fields excluded) SLO/summary denominators and alerts unchanged by shadow; shadow counted only in shadow_runs/kinds.shadow_validation
  - 증거: `{"nonzero_denominators": {"valid_calls": 55, "requests_received": 37, "eligible_requests": 37}, "shadow_runs": [4, 5], "before_hash": "c7f33075398529af", "after_hash": "c7f33075398529af", "validation": "val_84f211ef173545f4929360f37b2cd600", "side_effects": 0, "diff": []}`
- [통과] (retest) protected nodes and active_run_id pointers identical across the second shadow validation
  - 증거: `{"protected": {"Task": {"count": 29, "sha256": "e2894d895be6aef4"}, "Assignment": {"count": 19, "sha256": "dcd9403dc1fd8378"}, "Review": {"count": 37, "sha256": "67d284f4d6311cd9"}, "ReviewDecision": {"count": 19, "sha256": "924cb11e65f1bfb6"}, "Event": {"count": 597, "sha256": "d902eefee7b59147"}, "Request": {"count": 37, "sha256": "33c750e1a1881e89"}, "Judgment": {"count": 37, "sha256": "1f3e70e09f958056"}, "Correction": {"count": 11, "sha256": "b4504e5105de637c"}}, "pointers": 37}`
- [통과] journal records the shadow validation with run_kind='shadow'
  - 증거: `{"journal_rows": [{"kind": "shadow_validation", "run_kind": "shadow"}]}`
- [통과] ValidationRun (POST result == GET API == DB): conditions, sample counts, side_effects=0, run_kind=shadow
  - 증거: `{"retest_of_first_attempt": "first attempt looked up Run by ValidationRun id (stale after the F6 id split); retested via HAS_SHADOW_RUN", "validation": "val_ae2b8a074e3d412aa003c57a6efab5d4", "shadow_run": "run_shadow_a61b92f4dda34dd994dc11f709618207", "api_equals_db": {"sample_count": true, "labeled_count": true, "changed_count": true, "side_effects": true, "status": true, "run_kind": true, "base_config_version": true, "candidate_config_version": true, "max_calls": true, "calls": true, "human_correction_needed_base": true, "human_correction_needed_candidate": true}}`
- [브라우저 ui1: 통과] [X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족
  - 화면 값: `[{"ui_used": 16, "ui_out": 8, "db": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0}, "after": {"sample_count": 24, "corrections": 6, "review_transitions": 24, "failures": 0, "classification_changes": 16}, "used": {"sample_count": 16, "corrections": 3, "review_transitions": 16, "failures": 0, "classification_changes": 16}, "out_of_scope": {"sample_count": 8, "corrections": 3, "review_transitions": 8, "failures": 0, "classificat…`
- [브라우저 ui1: 통과] [X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족
  - 화면 값: `[{"ui_used": 16, "ui_out": 8, "db": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0}, "after": {"sample_count": 24, "corrections": 6, "review_transitions": 24, "failures": 0, "classification_changes": 16}, "used": {"sample_count": 16, "corrections": 3, "review_transitions": 16, "failures": 0, "classification_changes": 16}, "out_of_scope": {"sample_count": 8, "corrections": 3, "review_transitions": 8, "failures": 0, "classificat…`

### X05 — 통과

- [통과] post-publish in-scope requests: rule used, result changed (불필요→필요), APPLIED(before/after/version) == Judgment API == Trace rule step, Config pinned
  - 증거: `{"config_version": 2, "rule": "R-AI_NEED-01@1", "requests": [{"kind": "in_scope", "run_id": "run_2c5c765f9cbc4211b33f06e883bd0552", "api_ai_need": "필요", "db_ai_need": "필요", "model_raw_ai_need": "불필요", "api_rule_effects": [{"rule_version": "R-AI_NEED-01@1", "effect": "rule", "outcome": "used", "before": "불필요", "after": "필요", "config_version": 2}], "db_applied": [{"step": "step_30e7c2a911fc40f58ba3238032ba45b0", "kind": "rule", "rule": "R-AI_NEED-01@1", "outcome": "used", "before": "\"불필요\"", "after": "\"필요\"", "rv": "R-AI_NEED-01@1"}], "flow_config_version": 2, "flow_rule_steps": ["step_b70923f5d4d540409e2392221e6c4367", "step_30e7c2a911fc40f58ba3238032ba45b0"], "step_ids_in_applied": ["step_…`
- [통과] out-of-scope request: APPLIED out_of_scope recorded, classification NOT changed by the rule
  - 증거: `{"request": "req_6b09736cb81f40eb96a451f595f44c66", "probe": {"kind": "out_of_scope_probe", "run_id": "run_ca70aafc128d4634b4518075ee66995c", "api_ai_need": "불필요", "db_ai_need": "불필요", "model_raw_ai_need": "불필요", "api_rule_effects": [{"rule_version": "R-AI_NEED-01@1", "effect": "rule", "outcome": "out_of_scope", "before": "불필요", "after": "불필요", "config_version": 2}], "db_applied": [{"step": "step_3a8e4c6e9bc94cc58250723621fe7d75", "kind": "rule", "rule": "R-AI_NEED-01@1", "outcome": "out_of_scope", "before": "\"불필요\"", "after": "\"불필요\"", "rv": "R-AI_NEED-01@1"}], "flow_config_version": 2, "flow_rule_steps": ["step_e42e11c51bf44614a39fe9a601be05a9", "step_3a8e4c6e9bc94cc58250723621fe7d75"], …`
- [통과] pre-publication runs have no APPLIED rows for the rule (and still have their rule step)
  - 증거: `{"seed_requests": 8, "applied_rows": 0, "runs_with_rule_step": 8}`
- [**실패**] invariant-weakening rules (feasibility→가능, urgency→일반) are refused; no RuleVersion/Config created — _재시험으로 대체: stale expectation: after FIX-S the candidate save itself is refused (422), so the old 'candidate ok, version refused' shape no longer exists; replaced by the F4 checks_
  - 증거: `{"attempts": [{"attempt": "feasibility→가능", "candidate_status": 422, "candidate_body": "{\"detail\":{\"code\":\"RULE_INVARIANT\",\"reason\":\"action is outside the target safety allowlist\"}}"}, {"attempt": "urgency→일반", "candidate_status": 422, "candidate_body": "{\"detail\":{\"code\":\"RULE_INVARIANT\",\"reason\":\"action is outside the target safety allowlist\"}}"}], "config_validation_errors": [{"code": "RULE_INVARIANT", "reason": "Value error, RULE_INVARIANT: action is outside the target safety allowlist"}], "state_before": {"RuleVersion": {"count": 1, "sha256": "d1c34b14bd303783"}, "ConfigVersion": {"count": 2, "sha256": "49d807531b63f38a"}}, "state_after": {"RuleVersion": {"count": 1,…`
- [통과] lead_org rule applied to a new text-only request: APPLIED used (before→after) == Judgment API rule_effects; classification changed from the model value; both rules evaluated
  - 증거: `{"request": "req_1b06d22ddfbd4c26b4dfeef6ebfa2eb6", "run": "run_37c1373717254589994b666d8dc5f0d9", "applied": [{"step": "step_47ee821f73b24916b0799981d2b833c2", "rule": "R-AI_NEED-01@1", "outcome": "out_of_scope", "b": "\"혼합\"", "a": "\"혼합\""}, {"step": "step_47ee821f73b24916b0799981d2b833c2", "rule": "R-LEAD_ORG-01@1", "outcome": "used", "b": "\"IT팀\"", "a": "\"현업\""}], "api": [{"rule_version": "R-AI_NEED-01@1", "effect": "rule", "outcome": "out_of_scope", "before": "혼합", "after": "혼합", "config_version": 3}, {"rule_version": "R-LEAD_ORG-01@1", "effect": "rule", "outcome": "used", "before": "IT팀", "after": "현업", "config_version": 3}], "model_raw": "IT팀", "final": "현업"}`
- [통과] feasibility rule applied to a new text-only request: APPLIED used (before→after) == Judgment API rule_effects; value changed from the model output; every active rule evaluated
  - 증거: `{"request": "req_d5c5e1811fac42849b0260daa9e6e9aa", "run": "run_72bd2dbf13e043a2a1a3ed4b06377d0c", "applied": [{"step": "step_a4920d1256274c3db4d14c561ed044d4", "rule": "R-AI_NEED-01@1", "outcome": "used", "b": "\"불필요\"", "a": "\"필요\""}, {"step": "step_a4920d1256274c3db4d14c561ed044d4", "rule": "R-FEASIBILITY-01@1", "outcome": "used", "b": "\"정보 부족\"", "a": "\"조건부 가능\""}, {"step": "step_a4920d1256274c3db4d14c561ed044d4", "rule": "R-LEAD_ORG-01@1", "outcome": "out_of_scope", "b": "\"IT팀\"", "a": "\"IT팀\""}], "api": [{"rule_version": "R-AI_NEED-01@1", "effect": "rule", "outcome": "used", "before": "불필요", "after": "필요", "config_version": 4}, {"rule_version": "R-LEAD_ORG-01@1", "effect": "rule",…`
- [브라우저 ui1: 통과] [X05] Trace: "규칙 적용" step of an in-scope run shows the stored judgment; out-of-scope run keeps the model value
  - 화면 값: `[{"used": {"request": "req_b7638d574aa7420e8c8e632e206247d8", "run": "run_2c5c765f9cbc4211b33f06e883bd0552", "step": "step_30e7c2a911fc40f58ba3238032ba45b0", "shows_rule_version": true, "shows_before_after": false}, "out_of_scope": {"request": "req_6b09736cb81f40eb96a451f595f44c66", "run": "run_ca70aafc128d4634b4518075ee66995c", "step": "step_3a8e4c6e9bc94cc58250723621fe7d75", "shows_rule_version": true, "shows_before_after": false}}]`
- [브라우저 r1: 통과] [F3][X05] Observatory Trace "규칙 적용" step detail lists rule_id@version, outcome and before/after for every rule (used, out_of_scope, multi-rule) = step API = stored APPLIED
  - 화면 값: `[{"used": {"request": "req_b7638d574aa7420e8c8e632e206247d8", "run": "run_2c5c765f9cbc4211b33f06e883bd0552", "step": "step_30e7c2a911fc40f58ba3238032ba45b0", "rows": [{"rule": "R-AI_NEED-01@1", "outcome": "used", "before": "불필요", "after": "필요"}]}, "out_of_scope": {"request": "req_6b09736cb81f40eb96a451f595f44c66", "run": "run_ca70aafc128d4634b4518075ee66995c", "step": "step_3a8e4c6e9bc94cc58250723621fe7d75", "rows": [{"rule": "R-AI_NEED-01@1", "outcome": "out_of_scope", "before": "불필요", "after":…`
- [브라우저 r1: 통과] [X02][X05] lead_org rule on the learning screen: candidate → decision → version → shadow validation → published, application count = stored APPLIED
  - 화면 값: `[{"rule": "R-LEAD_ORG-01@1", "action": {"set": "현업"}, "applications": 14, "validation": "val_e8697532f8bc4b8cabcee5205d372aba"}]`
- [브라우저 ui1: 통과] [X05] Trace: "규칙 적용" step of an in-scope run shows the stored judgment; out-of-scope run keeps the model value
  - 화면 값: `[{"used": {"request": "req_b7638d574aa7420e8c8e632e206247d8", "run": "run_2c5c765f9cbc4211b33f06e883bd0552", "step": "step_30e7c2a911fc40f58ba3238032ba45b0", "shows_rule_version": true, "shows_before_after": false}, "out_of_scope": {"request": "req_6b09736cb81f40eb96a451f595f44c66", "run": "run_ca70aafc128d4634b4518075ee66995c", "step": "step_3a8e4c6e9bc94cc58250723621fe7d75", "shows_rule_version": true, "shows_before_after": false}}]`

### X06 — 통과

- [통과] graph API[request] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 58, "edge_count": 56, "layers": {"1": 37, "2": 3, "3": 13, "4": 3, "5": 2}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[run] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 58, "edge_count": 56, "layers": {"1": 37, "2": 3, "3": 13, "4": 3, "5": 2}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[rule2] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 18, "edge_count": 17, "layers": {"1": 9, "2": 1, "3": 4, "4": 3, "5": 1}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[rule_ai_need] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 43, "edge_count": 42, "layers": {"1": 10, "2": 1, "3": 5, "4": 3, "5": 24}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[config_2] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 18, "edge_count": 17, "layers": {"1": 10, "2": 1, "3": 5, "4": 2, "5": 0}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[candidate_status] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 80, "edge_count": 98, "layers": {"1": 25, "2": 4, "3": 17, "4": 10, "5": 24}, "missing_in_api": [], "extra_in_api": []}`
- [통과] reverse trace: business step → rule version → decision → candidate → correction → model output → source span (UI-independent /path == Cypher chain)
  - 증거: `{"run_step": "step_a4920d1256274c3db4d14c561ed044d4", "chains": [{"step": "step_a4920d1256274c3db4d14c561ed044d4", "rv": "R-FEASIBILITY-01@1", "d": "rdec_65ada79162344602b90a1ae72c736684", "c": "cand_79f6d9ca44e33854681ab0b0", "cor": "cor_88104cfdf04742de93884ec0aa95a41f", "o": "mout_b896ac7666e045a297e3424e1a3654c9", "e": "esp_00bcd34b6147453d9ce1aa6d1bfde782"}, {"step": "step_a4920d1256274c3db4d14c561ed044d4", "rv": "R-FEASIBILITY-01@1", "d": "rdec_65ada79162344602b90a1ae72c736684", "c": "cand_79f6d9ca44e33854681ab0b0", "cor": "cor_f53eaee7e65f4d4a97866d464f631bec", "o": "mout_1c4e0b450f0742c3b8096da917a7e74b", "e": "esp_5406be984af944e2b3032d16c1f079fe"}, {"step": "step_a4920d1256274c3db4…`
- [통과] forward trace: source span → model output → correction → candidate → decision → rule version → business step (rule applied to the new request)
  - 증거: `{"span": "esp_00bcd34b6147453d9ce1aa6d1bfde782", "downstream_count": 10, "reaches_step": "step_a4920d1256274c3db4d14c561ed044d4", "path": ["esp_00bcd34b6147453d9ce1aa6d1bfde782", "mout_b896ac7666e045a297e3424e1a3654c9", "cor_88104cfdf04742de93884ec0aa95a41f", "cand_79f6d9ca44e33854681ab0b0", "rdec_65ada79162344602b90a1ae72c736684", "R-FEASIBILITY-01@1", "step_a4920d1256274c3db4d14c561ed044d4"]}`
- [통과] node detail refs carry the same IDs as Flow/Learning (request_id, run_id, step_id, rule_id, rule_version, config_version)
  - 증거: `{"refs": {"run_id": "run_72bd2dbf13e043a2a1a3ed4b06377d0c", "request_id": "req_d5c5e1811fac42849b0260daa9e6e9aa", "step_id": "step_a4920d1256274c3db4d14c561ed044d4"}, "source_link_null_without_can_read_source": true}`
- [브라우저 ui1: **failed**] [X06] judgment map: nodes/edges = graph API = DB, bottom-up trace to source span, top-down trace, list view keyboard, Flow/Topology/Learning IDs — Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeAttached[2m([22m[2m)[22m failed
- [브라우저 r1: **failed**] [EVID][X06] text-only request: chat EvidenceSpan nodes are on the map (evidence layer), the cited span is reachable from the business step on the map — Error: [2mexpect([22m[31mreceived[39m[2m).[22mtoEqual[2m([22m[32mexpected[39m[2m) // deep equality[22m
- [브라우저 r1: 통과] [EVID][X06] text-only request: chat EvidenceSpan nodes are on the map (evidence layer), the cited span is reachable from the business step on the map
  - 화면 값: `[{"request": "req_d5c5e1811fac42849b0260daa9e6e9aa", "span_nodes_on_map": ["esp_00bcd34b6147453d9ce1aa6d1bfde782", "esp_5406be984af944e2b3032d16c1f079fe", "esp_c9e7262214c943eabe7a37e332f75154", "esp_df1e8a54e1a5433a9b2c4e038e56e845"], "cited": ["esp_c9e7262214c943eabe7a37e332f75154"], "stored_sources": ["chat"]}]`
- [브라우저 ui1: **timedOut**] [X06] judgment map: nodes/edges = graph API = DB, bottom-up trace to source span, top-down trace, list view keyboard, Flow/Topology/Learning IDs — [31mTest timeout of 150000ms exceeded.[39m
- [브라우저 ui1: 통과] [X06] judgment map: nodes/edges = graph API = DB, bottom-up trace to source span, top-down trace, list view keyboard, Flow/Topology/Learning IDs
  - 화면 값: `[{"map_nodes": 58, "map_edges": 56, "flow_href": "/observatory?run_id=run_72bd2dbf13e043a2a1a3ed4b06377d0c", "learning_href": "/learning"}, {"rule_map": [18, 17]}]`
- [브라우저 ui2: **failed**] [X06] criteria filters (request / rule / Config version / status), zoom controls — counts follow the graph API — Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoHaveAttribute[2m([22m[32mexpected[39m[2m)[22m failed
- [브라우저 ui2: **failed**] [X06] criteria filters (request / rule / Config version / status), zoom controls — counts follow the graph API — Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoHaveAttribute[2m([22m[32mexpected[39m[2m)[22m failed
- [브라우저 ui2: 통과] [X06] criteria filters (request / rule / Config version / status), zoom controls — counts follow the graph API
  - 화면 값: `[{"request_id": [58, 56], "rule_id": [23, 22], "config_version": [18, 17], "status_published": [81, 100]}]`
- [브라우저 ui2: 통과] [X06] criteria filters (request / rule / Config version / status), zoom controls — counts follow the graph API
  - 화면 값: `[{"request_id": [58, 56], "rule_id": [23, 22], "config_version": [18, 17], "status_published": [81, 100]}]`
- [브라우저 ui2: 통과] [X06] criteria filters (request / rule / Config version / status), zoom controls — counts follow the graph API
  - 화면 값: `[{"request_id": [58, 56], "rule_id": [23, 22], "config_version": [18, 17], "status_published": [81, 100]}]`
- [브라우저 ui2: 통과] [X06] criteria filters (request / rule / Config version / status), zoom controls — counts follow the graph API
  - 화면 값: `[{"request_id": [58, 56], "rule_id": [23, 22], "config_version": [18, 17], "status_published": [81, 100]}]`

### X07 — 통과

- [**실패**] in-flight run started before the stop keeps the pinned (old) Config version and still applies the rule — _재시험으로 대체: stop landed while the run was still pending (not started); retested after the run pinned its Config_
  - 증거: `{"request": "req_4f64895718614271894b4fb1193202ff", "run": "run_6c83a7f407af47c98dd6d9aefd71e746", "run_status_when_stop_called": {"id": "run_6c83a7f407af47c98dd6d9aefd71e746", "status": "pending", "cfg": null}, "run_config_version": 5, "stop_config_version": 5, "applied": [{"rule": "R-LEAD_ORG-01@1", "outcome": "out_of_scope"}, {"rule": "R-FEASIBILITY-01@1", "outcome": "out_of_scope"}], "judgment_committed": "2026-10-03T12:42:30.234Z", "ai_need": "불필요"}`
- [통과] after stop: active rules lack the rule; new request has no APPLIED for it and keeps the model value (불필요)
  - 증거: `{"request": "req_86170fbfe48e4a668f38914f738360d4", "run": "run_521d9511612545ce82e4770a937a81e0", "active_config": 5, "active_rules": ["R-LEAD_ORG-01@1", "R-FEASIBILITY-01@1"], "applied": [{"rule": "R-LEAD_ORG-01@1", "outcome": "out_of_scope"}, {"rule": "R-FEASIBILITY-01@1", "outcome": "out_of_scope"}], "ai_need": "불필요"}`
- [통과] publish v2 then revert to v1 = new Config versions each; v2 used before, v1 used after (APPLIED rule_version), Config pinned per run
  - 증거: `{"stop_cfg": 5, "v2_cfg": 6, "revert_cfg": 7, "v2_request": {"req": "req_ffb17c16c9b545beb734728696da558a", "applied": [{"rule": "R-LEAD_ORG-01@1", "outcome": "out_of_scope"}, {"rule": "R-FEASIBILITY-01@1", "outcome": "out_of_scope"}, {"rule": "R-AI_NEED-01@2", "outcome": "used"}]}, "revert_request": {"req": "req_e69c48ef3dfa45c88198a8451420164c", "applied": [{"rule": "R-AI_NEED-01@1", "outcome": "used"}, {"rule": "R-LEAD_ORG-01@1", "outcome": "out_of_scope"}, {"rule": "R-FEASIBILITY-01@1", "outcome": "out_of_scope"}]}, "rule_version_status": [{"v": 1, "s": "published"}, {"v": 2, "s": "reverted"}], "active_rules": ["R-LEAD_ORG-01@1", "R-FEASIBILITY-01@1", "R-AI_NEED-01@1"]}`
- [통과] past records unchanged: earlier APPLIED rows (before/after/outcome), earlier Judgments (hash), earlier Config versions identical
  - 증거: `{"applied_rows_before": 39, "applied_rows_now": 39, "judgments_checked": 24, "config_versions_checked": 4}`
- [통과] (retest) run in flight when the stop was published keeps the pinned old Config version and applies the rule; the stop is a new Config version
  - 증거: `{"attempt": 1, "request": "req_e8f1978855af49d9be5425991e13d20f", "run": "run_6a589d0855d74739b6ebbf4fc5ce3228", "state_when_stop_called": {"id": "run_6a589d0855d74739b6ebbf4fc5ce3228", "status": "running", "cfg": 7, "committed": false}, "active_config_before_stop": 7, "stop_config": 8, "run_config_version": 7, "judgment_committed_at": "2026-10-03T12:42:48.669Z", "applied": [{"rule": "R-AI_NEED-01@1", "outcome": "used", "before": "\"불필요\"", "after": "\"필요\""}, {"rule": "R-LEAD_ORG-01@1", "outcome": "out_of_scope", "before": "\"IT팀\"", "after": "\"IT팀\""}, {"rule": "R-FEASIBILITY-01@1", "outcome": "out_of_scope", "before": "\"정보 부족\"", "after": "\"정보 부족\""}], "ai_need": "필요"}`
- [브라우저 ui2: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 9, "v1": {"applications": 26, "configs": [2, 7, 9]}, "v2": {"applications": 1, "configs": [6]}, "configs": {"revert": 7, "stop": 5, "v2": 6}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 21시 28분 37초 · code:candidate@v1\n범위 수정 후 승인\napprove_with_scope_change. 사유: T38: 범위를 임상·규제 신호 낮음으로 확정. 확정 범위 {\"all\": [{\"field\": \"ai_need\", \"op\": \"eq\", \"value\": \"불필요\"}, {\"field\": \"lead_org\", \"op\": \"eq\", \"value\": \"IT팀\"}, {\"op\": \"lte\", \"signal\": \"clinical_saf…`
- [브라우저 ui2: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 9, "v1": {"applications": 26, "configs": [2, 7, 9]}, "v2": {"applications": 1, "configs": [6]}, "configs": {"revert": 7, "stop": 5, "v2": 6}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 21시 28분 37초 · code:candidate@v1\n범위 수정 후 승인\napprove_with_scope_change. 사유: T38: 범위를 임상·규제 신호 낮음으로 확정. 확정 범위 {\"all\": [{\"field\": \"ai_need\", \"op\": \"eq\", \"value\": \"불필요\"}, {\"field\": \"lead_org\", \"op\": \"eq\", \"value\": \"IT팀\"}, {\"op\": \"lte\", \"signal\": \"clinical_saf…`
- [브라우저 ui3: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 9, "v1": {"applications": 27, "configs": [2, 7, 9]}, "v2": {"applications": 1, "configs": [6]}, "configs": {"revert": 7, "stop": 5, "v2": 6}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 21시 28분 37초 · code:candidate@v1\n범위 수정 후 승인\napprove_with_scope_change. 사유: T38: 범위를 임상·규제 신호 낮음으로 확정. 확정 범위 {\"all\": [{\"field\": \"ai_need\", \"op\": \"eq\", \"value\": \"불필요\"}, {\"field\": \"lead_org\", \"op\": \"eq\", \"value\": \"IT팀\"}, {\"op\": \"lte\", \"signal\": \"clinical_saf…`
- [브라우저 ui3: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 9, "v1": {"applications": 27, "configs": [2, 7, 9]}, "v2": {"applications": 1, "configs": [6]}, "configs": {"revert": 7, "stop": 5, "v2": 6}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 21시 28분 37초 · code:candidate@v1"}]`

### X08 — 통과

- [통과] API server + worker + collector restarted: DB truth and public API snapshot before/after differ in 0 fields (candidates, decisions, rule versions, relations, APPLIED rows, validation cards, configs, graph, effects)
  - 증거: `{"differences": [], "difference_count": 0, "compared": {"db": {"applied": 52, "candidates": 6, "chat_spans": 102, "configs": 9, "corrections": 11, "inv_applied": 2, "rule_versions": 6, "shadow_runs": 5, "validations": 5}, "api_candidates": 6, "api_rules": 5, "graph_criteria": 6, "graph_nodes": {"candidate_status": 94, "config_2": 18, "request": 58, "rule2": 23, "rule_ai_need": 47, "run": 58}, "graph_edges": {"candidate_status": 119, "config_2": 17, "request": 56, "rule2": 22, "rule_ai_need": 46, "run": 56}, "judgments": 9}, "pre_sha": "eee93324f597d0fe", "post_sha": "eee93324f597d0fe"}`
- [통과] after restart the new worker processes a new request under the active Config and applies the restored rule (APPLIED recorded)
  - 증거: `{"request": "req_01626ab5ff9e4a64bd4620528eaf53dd", "run": "run_ca76571f8f02467bb1f80045c8299d93", "active_config": 9, "applied": [{"rule": "R-AI_NEED-01@1", "outcome": "used", "before": "\"불필요\"", "after": "\"필요\""}, {"rule": "R-LEAD_ORG-01@1", "outcome": "out_of_scope", "before": "\"IT팀\"", "after": "\"IT팀\""}, {"rule": "R-FEASIBILITY-01@1", "outcome": "out_of_scope", "before": "\"정보 부족\"", "after": "\"정보 부족\""}], "ai_need": "필요"}`
- [**실패**] after restart + one new request, stored learning state is unchanged (corrections, candidates, rule versions, validations, Configs equal) and graph differences are only the new request's own nodes (none removed) — _재시험으로 대체: 같은 항목을 수정·재실행해 통과(시험 코드 정정 후, 아래 이력 참조)_
  - 증거: `{"unchanged_db": {"corrections": true, "candidates": true, "rule_versions": false, "validations": true, "configs": true}, "removed": {"candidate_status": [], "config_2": [], "request": [], "rule2": [], "rule_ai_need": [], "run": []}, "added_not_owned_by_new_request": {"candidate_status": [], "config_2": [], "request": [], "rule2": [], "rule_ai_need": [], "run": []}, "new_request": "req_01626ab5ff9e4a64bd4620528eaf53dd"}`
- [통과] after restart + one new request, stored learning state is unchanged (corrections, candidates, rule versions, validations, Configs equal) and graph differences are only the new request's own nodes (none removed)
  - 증거: `{"unchanged_db": {"corrections": true, "candidates": true, "validations": true, "configs": true, "rule_versions(id,status,body,configs)": true}, "removed": {"candidate_status": [], "config_2": [], "request": [], "rule2": [], "rule_ai_need": [], "run": []}, "added_not_owned_by_new_request": {"candidate_status": [], "config_2": [], "request": [], "rule2": [], "rule_ai_need": [], "run": []}, "new_request": "req_01626ab5ff9e4a64bd4620528eaf53dd", "application_count_growth_per_rule_version": {"R-AI_NEED-01@1": 1, "R-AI_NEED-01@2": 0, "R-AI_NEED-02@1": 0, "R-AI_NEED-03@1": 0, "R-FEASIBILITY-01@1": 1, "R-LEAD_ORG-01@1": 1}}`
- [브라우저 ui2: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 9, "v1": {"applications": 26, "configs": [2, 7, 9]}, "v2": {"applications": 1, "configs": [6]}, "configs": {"revert": 7, "stop": 5, "v2": 6}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 21시 28분 37초 · code:candidate@v1\n범위 수정 후 승인\napprove_with_scope_change. 사유: T38: 범위를 임상·규제 신호 낮음으로 확정. 확정 범위 {\"all\": [{\"field\": \"ai_need\", \"op\": \"eq\", \"value\": \"불필요\"}, {\"field\": \"lead_org\", \"op\": \"eq\", \"value\": \"IT팀\"}, {\"op\": \"lte\", \"signal\": \"clinical_saf…`
- [브라우저 ui2: **failed**] [X08] judgment map and trace: counts and IDs equal the stored snapshot after reload — Error: ENOENT: no such file or directory, open '/Users/psw/Projects/decision-chat-bot/artifacts/validation/20261003T122747Z/extension/snap.pre.json'
- [브라우저 ui2: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 9, "v1": {"applications": 26, "configs": [2, 7, 9]}, "v2": {"applications": 1, "configs": [6]}, "configs": {"revert": 7, "stop": 5, "v2": 6}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 21시 28분 37초 · code:candidate@v1\n범위 수정 후 승인\napprove_with_scope_change. 사유: T38: 범위를 임상·규제 신호 낮음으로 확정. 확정 범위 {\"all\": [{\"field\": \"ai_need\", \"op\": \"eq\", \"value\": \"불필요\"}, {\"field\": \"lead_org\", \"op\": \"eq\", \"value\": \"IT팀\"}, {\"op\": \"lte\", \"signal\": \"clinical_saf…`
- [브라우저 ui2: 통과] [X08] judgment map and trace: counts and IDs equal the stored snapshot after reload
  - 화면 값: `[{"checked": {"candidate_status": [94, 119], "config_2": [18, 17], "request": [58, 56], "rule2": [23, 22], "rule_ai_need": [47, 46], "run": [58, 56]}}]`
- [브라우저 ui3: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 9, "v1": {"applications": 27, "configs": [2, 7, 9]}, "v2": {"applications": 1, "configs": [6]}, "configs": {"revert": 7, "stop": 5, "v2": 6}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 21시 28분 37초 · code:candidate@v1\n범위 수정 후 승인\napprove_with_scope_change. 사유: T38: 범위를 임상·규제 신호 낮음으로 확정. 확정 범위 {\"all\": [{\"field\": \"ai_need\", \"op\": \"eq\", \"value\": \"불필요\"}, {\"field\": \"lead_org\", \"op\": \"eq\", \"value\": \"IT팀\"}, {\"op\": \"lte\", \"signal\": \"clinical_saf…`
- [브라우저 ui3: **failed**] [X08] judgment map and trace: counts and IDs equal the stored snapshot after reload — Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoHaveAttribute[2m([22m[32mexpected[39m[2m)[22m failed
- [브라우저 r3: 통과] [X08][F6] validation card is read from the server after API/worker restart and a reload: id, sample, changed, side effects, calls = DB = API; shadow Run id differs from the ValidationRun id
  - 화면 값: `[{"validation": "val_ae2b8a074e3d412aa003c57a6efab5d4", "api": {"sample": 8, "changed": 8, "side": 0}, "shadow_runs": 5}]`
- [브라우저 ui3: **failed**] [X08] judgment map and trace: counts and IDs equal the stored snapshot after reload — Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoHaveAttribute[2m([22m[32mexpected[39m[2m)[22m failed
- [브라우저 ui3: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 9, "v1": {"applications": 27, "configs": [2, 7, 9]}, "v2": {"applications": 1, "configs": [6]}, "configs": {"revert": 7, "stop": 5, "v2": 6}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 21시 28분 37초 · code:candidate@v1"}]`
- [브라우저 ui3: 통과] [X08] judgment map and trace: counts and IDs equal the stored snapshot after reload
  - 화면 값: `[{"checked": {"candidate_status": [95, 122], "config_2": [18, 17], "request": [58, 56], "rule2": [24, 23], "rule_ai_need": [48, 47], "run": [58, 56]}}]`

### X09 — 통과

- [통과] effects API counts (before/after/used/out_of_scope: sample, change, correction, review, failure) == independent DB computation
  - 증거: `{"api": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0, "latency_sample_count": 8, "latency_p50_ms": 3501.0, "latency_p95_ms": 3657.0}, "after": {"sample_count": 4, "corrections": 0, "review_transitions": 4, "failures": 0, "classification_changes": 3, "latency_sample_count": 4, "latency_p50_ms": 3534.0, "latency_p95_ms": 4479.75}, "used": {"sample_count": 3, "corrections": 0, "review_transitions": 3, "failures": 0, "classification_changes": 3, "latency_sample_count": 3, "latency_p50_ms": 3434.0, "latency_p95_ms": 3614.0}, "out_of_scope": {"sample_count": 1, "corrections": 0, "review_transitions": 1, "failures": 0, "classif…`
- [통과] sample below minimum -> effect 'insufficient_sample' (undetermined), shadow runs excluded, SLO not included
  - 증거: `{"effect": "insufficient_sample", "minimum_sample": 20, "samples": 12, "shadow_runs_excluded": 1, "slo_included": false}`
- [브라우저 ui1: 통과] [X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족
  - 화면 값: `[{"ui_used": 16, "ui_out": 8, "db": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0}, "after": {"sample_count": 24, "corrections": 6, "review_transitions": 24, "failures": 0, "classification_changes": 16}, "used": {"sample_count": 16, "corrections": 3, "review_transitions": 16, "failures": 0, "classification_changes": 16}, "out_of_scope": {"sample_count": 8, "corrections": 3, "review_transitions": 8, "failures": 0, "classificat…`
- [브라우저 ui1: 통과] [X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족
  - 화면 값: `[{"ui_used": 16, "ui_out": 8, "db": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0}, "after": {"sample_count": 24, "corrections": 6, "review_transitions": 24, "failures": 0, "classification_changes": 16}, "used": {"sample_count": 16, "corrections": 3, "review_transitions": 16, "failures": 0, "classification_changes": 16}, "out_of_scope": {"sample_count": 8, "corrections": 3, "review_transitions": 8, "failures": 0, "classificat…`

### F3 Trace 규칙 적용 단계 상세 — 통과

- [통과] Trace step detail API rule_applications (rule_id@version, outcome, before/after) == stored APPLIED rows (in-scope: used 불필요→필요; out-of-scope: out_of_scope)
  - 증거: `{"in_scope": {"request": "req_b7638d574aa7420e8c8e632e206247d8", "run": "run_2c5c765f9cbc4211b33f06e883bd0552", "step": "step_30e7c2a911fc40f58ba3238032ba45b0", "api_rule_applications": [{"rule_version": "R-AI_NEED-01@1", "rule_id": "R-AI_NEED-01", "version": 1, "effect": "rule", "outcome": "used", "before": "불필요", "after": "필요", "config_versions": [2]}], "db_applied": [{"rule": "R-AI_NEED-01@1", "rule_id": "R-AI_NEED-01", "version": 1, "outcome": "used", "before": "\"불필요\"", "after": "\"필요\""}], "config_version": 2, "flow_node_kind": "rule", "equal": true}, "out_of_scope": {"request": "req_6b09736cb81f40eb96a451f595f44c66", "run": "run_ca70aafc128d4634b4518075ee66995c", "step": "step_3a8e4c…`
- [브라우저 r1: 통과] [F3][X05] Observatory Trace "규칙 적용" step detail lists rule_id@version, outcome and before/after for every rule (used, out_of_scope, multi-rule) = step API = stored APPLIED
  - 화면 값: `[{"used": {"request": "req_b7638d574aa7420e8c8e632e206247d8", "run": "run_2c5c765f9cbc4211b33f06e883bd0552", "step": "step_30e7c2a911fc40f58ba3238032ba45b0", "rows": [{"rule": "R-AI_NEED-01@1", "outcome": "used", "before": "불필요", "after": "필요"}]}, "out_of_scope": {"request": "req_6b09736cb81f40eb96a451f595f44c66", "run": "run_ca70aafc128d4634b4518075ee66995c", "step": "step_3a8e4c6e9bc94cc58250723621fe7d75", "rows": [{"rule": "R-AI_NEED-01@1", "outcome": "out_of_scope", "before": "불필요", "after":…`

### F4 불변 조건 허용 목록·blocked_by_invariant — 통과

- [통과] candidate save: feasibility→가능, urgency→일반, urgency→판단 보류 are 422 RULE_INVARIANT for reviewer and rule_admin; no candidate stored
  - 증거: `{"attempts": [{"role": "reviewer", "field": "feasibility", "value": "가능", "status": 422, "code": "RULE_INVARIANT"}, {"role": "rule_admin", "field": "feasibility", "value": "가능", "status": 422, "code": "RULE_INVARIANT"}, {"role": "reviewer", "field": "urgency", "value": "일반", "status": 422, "code": "RULE_INVARIANT"}, {"role": "rule_admin", "field": "urgency", "value": "일반", "status": 422, "code": "RULE_INVARIANT"}, {"role": "reviewer", "field": "urgency", "value": "판단 보류", "status": 422, "code": "RULE_INVARIANT"}, {"role": "rule_admin", "field": "urgency", "value": "판단 보류", "status": 422, "code": "RULE_INVARIANT"}], "candidates_before": 2, "candidates_after": 2}`
- [통과] Config publish/validate with weakening rule is refused (422) and no Config version is created
  - 증거: `{"attempts": [{"rule": "urgency→판단 보류", "publish_status": 422, "publish_code": "RULE_INVARIANT", "validate_status": 200, "validate_body": "{\"valid\":false,\"config\":null,\"errors\":[{\"code\":\"RULE_INVARIANT\",\"reason\":\"Value error, RULE_INVARIANT: action is outside the target safety allowlist\"}]}"}, {"rule": "feasibility→가능", "publish_status": 422, "publish_code": "RULE_INVARIANT", "validate_status": 200, "validate_body": "{\"valid\":false,\"config\":null,\"errors\":[{\"code\":\"RULE_INVARIANT\",\"reason\":\"Value error, RULE_INVARIANT: action is outside the target safety allowlist\"}]}"}], "active_config": 2}`
- [통과] candidate save: feasibility→가능, urgency→일반, urgency→판단 보류 are 422 RULE_INVARIANT for reviewer and rule_admin; no candidate stored
  - 증거: `{"attempts": [{"role": "reviewer", "field": "feasibility", "value": "가능", "status": 422, "code": "RULE_INVARIANT"}, {"role": "rule_admin", "field": "feasibility", "value": "가능", "status": 422, "code": "RULE_INVARIANT"}, {"role": "reviewer", "field": "urgency", "value": "일반", "status": 422, "code": "RULE_INVARIANT"}, {"role": "rule_admin", "field": "urgency", "value": "일반", "status": 422, "code": "RULE_INVARIANT"}, {"role": "reviewer", "field": "urgency", "value": "판단 보류", "status": 422, "code": "RULE_INVARIANT"}, {"role": "rule_admin", "field": "urgency", "value": "판단 보류", "status": 422, "code": "RULE_INVARIANT"}], "candidates_before": 2, "candidates_after": 2}`
- [통과] Config publish/validate with weakening rule is refused (422) and no Config version is created
  - 증거: `{"attempts": [{"rule": "urgency→판단 보류", "publish_status": 422, "publish_code": "RULE_INVARIANT", "validate_status": 200, "validate_body": "{\"valid\":false,\"config\":null,\"errors\":[{\"code\":\"RULE_INVARIANT\",\"reason\":\"Value error, RULE_INVARIANT: action is outside the target safety allowlist\"}]}"}, {"rule": "feasibility→가능", "publish_status": 422, "publish_code": "RULE_INVARIANT", "validate_status": 200, "validate_body": "{\"valid\":false,\"config\":null,\"errors\":[{\"code\":\"RULE_INVARIANT\",\"reason\":\"Value error, RULE_INVARIANT: action is outside the target safety allowlist\"}]}"}], "active_config": 2}`
- [통과] publish of a DB-injected violating rule version is refused (422 RULE_INVARIANT); Config unchanged
  - 증거: `{"attempts": [{"rule": "R-URGENCY-91", "status": 422, "code": "RULE_INVARIANT"}, {"rule": "R-FEASIBILITY-92", "status": 422, "code": "RULE_INVARIANT"}], "config": 1, "tenant": "t-x38r-10031227i"}`
- [통과] DB-injected violating rules (urgency→판단 보류, feasibility→가능) are recorded blocked_by_invariant at apply time; classification = model output; APPLIED = Judgment API = Trace step API
  - 증거: `{"tenant": "t-x38r-10031227i", "request": "req_c89f7bb6abf549efbee8e901316c260c", "run": "run_30b0b4829e9047b9adb4d6136b3d1e09", "config_version": 2, "applied": [{"step": "step_34a8e70ab52e4436bfd0166122c6d5d1", "rule": "R-FEASIBILITY-92@1", "outcome": "blocked_by_invariant", "before": "\"정보 부족\"", "after": "\"정보 부족\""}, {"step": "step_34a8e70ab52e4436bfd0166122c6d5d1", "rule": "R-URGENCY-91@1", "outcome": "blocked_by_invariant", "before": "\"판단 보류\"", "after": "\"판단 보류\""}], "model_raw": {"feasibility": "정보 부족", "urgency": "판단 보류"}, "final": {"urgency": "판단 보류", "feasibility": "정보 부족"}, "api_rule_effects": [{"rule_version": "R-URGENCY-91@1", "effect": "rule", "outcome": "blocked_by_invarian…`
- [브라우저 r1: 통과] [F4] Trace shows blocked_by_invariant for the violating rules written straight into the DB; the classification stays the model value
  - 화면 값: `[{"tenant": "t-x38r-10031227i", "request": "req_c89f7bb6abf549efbee8e901316c260c", "shown": [{"rule": "R-FEASIBILITY-92@1", "outcome": "blocked_by_invariant", "before": "정보 부족", "after": "정보 부족"}, {"rule": "R-URGENCY-91@1", "outcome": "blocked_by_invariant", "before": "판단 보류", "after": "판단 보류"}]}]`

### F5 자료 부족 승인 확인 — 통과

- [통과] 자료 부족 candidate approval without acknowledgement → 422 INSUFFICIENT_ACK_REQUIRED; with acknowledgement but reason <10 chars → 422; nothing stored
  - 증거: `{"candidate": "cand_e123faef72028b6d12635bef", "status": "자료 부족", "no_ack": [422, "INSUFFICIENT_ACK_REQUIRED"], "short_reason": [422, "INSUFFICIENT_ACK_REQUIRED"]}`
- [통과] acknowledged approval stored: decision.insufficient_approved=true, response/candidate detail show '자료 부족 상태로 승인됨', audit has reason
  - 증거: `{"decision": "rdec_86485b0355534353b4d3a4aec8ade3c1", "label": "자료 부족 상태로 승인됨", "db": {"ins": true, "action": "approve", "reason": "T38-R: 표본 2건뿐임을 확인하고 자료 부족 상태로 승인"}, "audit": [["rule.decision", "usr_t-x38r-10031227_rule_admin", "T38-R: 표본 2건뿐임을 확인하고 자료 부족 상태로 승인"]]}`
- [통과] rule version from an insufficient approval: refused without acknowledgement (422), created with it; version list shows the label
  - 증거: `{"no_ack": [422, "INSUFFICIENT_ACK_REQUIRED"], "version": "R-AI_NEED-02@1", "label": "자료 부족 상태로 승인됨"}`
- [통과] human candidate without supporting corrections is stored as '자료 부족' (UI approval target)
  - 증거: `{"candidate": "cand_0c4749cc88828c487a3d8ead", "status": "자료 부족"}`
- [통과] browser approval of the 자료 부족 candidate stored: decision.insufficient_approved=true with a ≥10-char reason, rule version (validating) created, API shows the label
  - 증거: `{"candidate": "cand_0c4749cc88828c487a3d8ead", "decision": [{"id": "rdec_84495d2d93af4a2083f886cb6bfe97cc", "ins": true, "reason": "T38-R 화면 시험: 지지 수정 0건 확인", "by": "usr_t-x38r-10031227_rule_admin"}], "versions": [{"id": "R-AI_NEED-03@1", "status": "validating"}], "label": "자료 부족 상태로 승인됨", "status": "approved"}`
- [브라우저 r1: 통과] [F5] 자료 부족 candidate: approve is disabled until the acknowledgement checkbox and a ≥10 character reason; afterwards "자료 부족 상태로 승인됨" is shown
  - 화면 값: `[{"candidate": "cand_0c4749cc88828c487a3d8ead", "api_label": "자료 부족 상태로 승인됨", "status": "approved"}]`

### F6 섀도 Run id 분리 — 통과

- [통과] every ValidationRun has its own shadow Run (id run_shadow_*, run_kind=shadow, != ValidationRun id); no Run shares a ValidationRun id; journal shadow rows are keyed by the shadow run id and tagged run_kind=shadow
  - 증거: `{"validations": [{"validation": "val_ae2b8a074e3d412aa003c57a6efab5d4", "shadow_run": "run_shadow_a61b92f4dda34dd994dc11f709618207", "rule": "R-AI_NEED-01@1"}, {"validation": "val_e8697532f8bc4b8cabcee5205d372aba", "shadow_run": "run_shadow_1335947c489b4ab297ef717994dc285b", "rule": "R-LEAD_ORG-01@1"}, {"validation": "val_c9703714627f4b33862c115123f71ef8", "shadow_run": "run_shadow_f9db69bc78d746e9a6ca6b4fd3c1e7c0", "rule": "R-FEASIBILITY-01@1"}, {"validation": "val_7c3f38b9de3c4741b418b6198f00fcdd", "shadow_run": "run_shadow_a3d841b58f5b473e9239dad250463c8b", "rule": "R-AI_NEED-01@2"}, {"validation": "val_84f211ef173545f4929360f37b2cd600", "shadow_run": "run_shadow_1c4da96d22864289a184d87e3…`
- [브라우저 r3: 통과] [X08][F6] validation card is read from the server after API/worker restart and a reload: id, sample, changed, side effects, calls = DB = API; shadow Run id differs from the ValidationRun id
  - 화면 값: `[{"validation": "val_ae2b8a074e3d412aa003c57a6efab5d4", "api": {"sample": 8, "changed": 8, "side": 0}, "shadow_runs": 5}]`

### F7 시각 직렬화(Flow/단계 상세) — 통과

- [통과] Flow nodes and step detail serialise started_at/ended_at as ISO-8601 strings (no `_DateTime__` internals)
  - 증거: `{"run": "run_2c5c765f9cbc4211b33f06e883bd0552", "nodes": 8, "sample": [["step_7dde2055fd904545b9698b8c6e84c717", "2026-10-03T12:29:18.162000000+00:00", "2026-10-03T12:29:18.238000000+00:00"], ["step_b70923f5d4d540409e2392221e6c4367", "2026-10-03T12:29:18.138000000+00:00", "2026-10-03T12:29:18.150000000+00:00"]], "bad": []}`

### 근거 계층(텍스트 전용 요청의 chat EvidenceSpan) — 통과

- [통과] text-only request (0 attachments): judgment map evidence layer contains the stored chat EvidenceSpan nodes (API node ids == Neo4j span ids)
  - 증거: `{"request": "req_d5c5e1811fac42849b0260daa9e6e9aa", "attachments": 0, "db_spans": 2, "api_span_nodes": ["esp_00bcd34b6147453d9ce1aa6d1bfde782", "esp_5406be984af944e2b3032d16c1f079fe", "esp_c9e7262214c943eabe7a37e332f75154", "esp_df1e8a54e1a5433a9b2c4e038e56e845"], "layer1": {"layer": 1, "name": "근거", "desc": "문서 구간 · 모델 반환값 · 사람 수정", "count": 37}, "sources": ["chat"]}`
- [통과] business step → rule version → decision → candidate → correction → model output → chat EvidenceSpan: Cypher chain == /graph/judgment/path (UI-independent)
  - 증거: `{"step": "step_a4920d1256274c3db4d14c561ed044d4", "chains": [{"step": "step_a4920d1256274c3db4d14c561ed044d4", "rv": "R-FEASIBILITY-01@1", "d": "rdec_65ada79162344602b90a1ae72c736684", "c": "cand_79f6d9ca44e33854681ab0b0", "cor": "cor_88104cfdf04742de93884ec0aa95a41f", "o": "mout_b896ac7666e045a297e3424e1a3654c9", "e": "esp_00bcd34b6147453d9ce1aa6d1bfde782", "source": "chat"}, {"step": "step_a4920d1256274c3db4d14c561ed044d4", "rv": "R-FEASIBILITY-01@1", "d": "rdec_65ada79162344602b90a1ae72c736684", "c": "cand_79f6d9ca44e33854681ab0b0", "cor": "cor_f53eaee7e65f4d4a97866d464f631bec", "o": "mout_1c4e0b450f0742c3b8096da917a7e74b", "e": "esp_5406be984af944e2b3032d16c1f079fe", "source": "chat"}, {…`
- [**실패**] text-only request (0 attachments): judgment map evidence layer shows the chat EvidenceSpan nodes cited by the run (API span node ids ⊇ Cypher CITES targets, ⊆ stored spans of the request) — _재시험으로 대체: too strict: the request map also contains the spans of the rule's supporting corrections; retested with the corrected expectation_
  - 증거: `{"request": "req_d5c5e1811fac42849b0260daa9e6e9aa", "attachments": 0, "stored_spans": 2, "cited_by_run": ["esp_c9e7262214c943eabe7a37e332f75154"], "api_span_nodes": ["esp_00bcd34b6147453d9ce1aa6d1bfde782", "esp_5406be984af944e2b3032d16c1f079fe", "esp_c9e7262214c943eabe7a37e332f75154", "esp_df1e8a54e1a5433a9b2c4e038e56e845"], "layer1": {"layer": 1, "name": "근거", "desc": "문서 구간 · 모델 반환값 · 사람 수정", "count": 37}, "sources": ["chat"]}`
- [통과] business step → rule version → decision → candidate → correction → model output → chat EvidenceSpan: Cypher chain == /graph/judgment/path (UI-independent)
  - 증거: `{"step": "step_a4920d1256274c3db4d14c561ed044d4", "chains": [{"step": "step_a4920d1256274c3db4d14c561ed044d4", "rv": "R-FEASIBILITY-01@1", "d": "rdec_65ada79162344602b90a1ae72c736684", "c": "cand_79f6d9ca44e33854681ab0b0", "cor": "cor_88104cfdf04742de93884ec0aa95a41f", "o": "mout_b896ac7666e045a297e3424e1a3654c9", "e": "esp_00bcd34b6147453d9ce1aa6d1bfde782", "source": "chat"}, {"step": "step_a4920d1256274c3db4d14c561ed044d4", "rv": "R-FEASIBILITY-01@1", "d": "rdec_65ada79162344602b90a1ae72c736684", "c": "cand_79f6d9ca44e33854681ab0b0", "cor": "cor_f53eaee7e65f4d4a97866d464f631bec", "o": "mout_1c4e0b450f0742c3b8096da917a7e74b", "e": "esp_5406be984af944e2b3032d16c1f079fe", "source": "chat"}, {…`
- [통과] text-only request (0 attachments): judgment map evidence layer shows the chat EvidenceSpan nodes cited by the run (API span node ids ⊇ Cypher CITES targets of the run; extra nodes = spans of the rule's supporting corrections)
  - 증거: `{"request": "req_d5c5e1811fac42849b0260daa9e6e9aa", "attachments": 0, "stored_spans": 2, "cited_by_run": ["esp_c9e7262214c943eabe7a37e332f75154"], "api_span_nodes": ["esp_00bcd34b6147453d9ce1aa6d1bfde782", "esp_5406be984af944e2b3032d16c1f079fe", "esp_c9e7262214c943eabe7a37e332f75154", "esp_df1e8a54e1a5433a9b2c4e038e56e845"], "support_correction_spans": ["esp_00bcd34b6147453d9ce1aa6d1bfde782", "esp_5406be984af944e2b3032d16c1f079fe", "esp_df1e8a54e1a5433a9b2c4e038e56e845"], "layer1": {"layer": 1, "name": "근거", "desc": "문서 구간 · 모델 반환값 · 사람 수정", "count": 37}, "sources": ["chat"]}`
- [통과] business step → rule version → decision → candidate → correction → model output → chat EvidenceSpan: Cypher chain == /graph/judgment/path (UI-independent)
  - 증거: `{"step": "step_a4920d1256274c3db4d14c561ed044d4", "chains": [{"step": "step_a4920d1256274c3db4d14c561ed044d4", "rv": "R-FEASIBILITY-01@1", "d": "rdec_65ada79162344602b90a1ae72c736684", "c": "cand_79f6d9ca44e33854681ab0b0", "cor": "cor_88104cfdf04742de93884ec0aa95a41f", "o": "mout_b896ac7666e045a297e3424e1a3654c9", "e": "esp_00bcd34b6147453d9ce1aa6d1bfde782", "source": "chat"}, {"step": "step_a4920d1256274c3db4d14c561ed044d4", "rv": "R-FEASIBILITY-01@1", "d": "rdec_65ada79162344602b90a1ae72c736684", "c": "cand_79f6d9ca44e33854681ab0b0", "cor": "cor_f53eaee7e65f4d4a97866d464f631bec", "o": "mout_1c4e0b450f0742c3b8096da917a7e74b", "e": "esp_5406be984af944e2b3032d16c1f079fe", "source": "chat"}, {…`
- [브라우저 r1: **failed**] [EVID][X06] text-only request: chat EvidenceSpan nodes are on the map (evidence layer), the cited span is reachable from the business step on the map — Error: [2mexpect([22m[31mreceived[39m[2m).[22mtoEqual[2m([22m[32mexpected[39m[2m) // deep equality[22m
- [브라우저 r1: 통과] [EVID][X06] text-only request: chat EvidenceSpan nodes are on the map (evidence layer), the cited span is reachable from the business step on the map
  - 화면 값: `[{"request": "req_d5c5e1811fac42849b0260daa9e6e9aa", "span_nodes_on_map": ["esp_00bcd34b6147453d9ce1aa6d1bfde782", "esp_5406be984af944e2b3032d16c1f079fe", "esp_c9e7262214c943eabe7a37e332f75154", "esp_df1e8a54e1a5433a9b2c4e038e56e845"], "cited": ["esp_c9e7262214c943eabe7a37e332f75154"], "stored_sources": ["chat"]}]`

## 4. X10 회귀

모두 이번 실행 중(2026-10-03, 이 tenant 시나리오 실행 뒤) 저장소 최신 코드로 재실행했다. 추가 환경변수 없음(`make up` 후 실행).

| 명령 | 결과 | 증거 |
| --- | --- | --- |
| `make test` | 백엔드 **136 통과·1 건너뜀**(live 전용), 프런트 vitest **37 통과**(11 파일) | `logs/make-test.log` |
| `make test-fault` (전용 컨테이너 7688) | **11/11 통과**(187.5초) | `artifacts/validation/t22/20261003T124810Z/`(junit.xml, report.md), `logs/make-test-fault.log` |
| `make test-acceptance` (ACC_PORT=8143, ACC_UI_PORT=5443, live Jev) | 백엔드 **40/40 통과**·UI(Playwright) **12/12 통과**, exit 0 | `artifacts/validation/t21/20261003t125137z-27336/`(junit.xml, ui-results.json), `logs/make-test-acceptance.log` |
| `X38_RUN=1 pytest tests/acceptance/extension` (확장 게이트 원장 검사) | **9 통과** | 이 폴더 `ledger.json` |
| `npx tsc --noEmit`(frontend) | 오류 없음 | — |

기존 게이트(G01–G12) 판정은 T27 소관이며 여기서는 재실행 결과만 인용한다.

## 5. 발견 사항

### 이전 실행(20261003T093618Z) 대비 변화

| 항목 | 이전 | 이번 재실행 |
| --- | --- | --- |
| F3 Trace '규칙 적용' 단계 상세 | 규칙 버전·전후 값 미표시(한계) | **해소**: `/api/observe/steps/{id}`가 `rule_applications`(rule_id@version·outcome·전후 값)를 반환하고 서랍 표가 같은 값을 표시. 사용(불필요→필요)·범위 밖·다중 규칙(규칙 3개 동시 평가)·`blocked_by_invariant` 모두 API=저장 APPLIED=화면 일치(F3 항목, `r1-f3-trace-*.png`) |
| F4 불변 조건 | 리터럴만 거절, urgency 긴급→판단 보류 규칙이 승인·게시됨 | **해소**: urgency→일반·판단 보류, feasibility→가능 모두 후보 저장 422 `RULE_INVARIANT`(reviewer·rule_admin), Config 게시 422, DB에 넣은 위반 RuleVersion 게시 422. DB에 직접 넣은 위반 Config 규칙은 적용 시 `blocked_by_invariant`로 기록되고 분류는 모델값 유지 |
| F5 자료 부족 후보 | 서버가 막지 않음 | **해소**: 확인 없이 승인 422 `INSUFFICIENT_ACK_REQUIRED`(사유 10자 미만도 422), 확인+사유 시 승인되고 '자료 부족 상태로 승인됨' 표시(API·화면·감사). 규칙 버전 생성도 같은 확인 필요 |
| F6 Run/ValidationRun 같은 id | 같은 `id` | **해소**: 섀도 Run은 `run_shadow_*`로 별도 id, `ValidationRun -[:HAS_SHADOW_RUN]-> Run`, journal은 섀도 run id로 `run_kind=shadow` 기록. 검증 5건 모두 분리 확인 |
| F7 시각 직렬화 | Flow 시각이 Neo4j 내부 구조 | **해소**(ISO 문자열) |
| 근거 계층 | 텍스트 전용 요청은 근거 노드 없음(모델 인용이 없는 문장 한정) | 텍스트만 제출한 요청에서도 chat EvidenceSpan(`source=chat`)이 저장되고 판단 맵 근거 계층에 노드로 표시, 업무(RunStep)→규칙 버전→결정→후보→수정→모델 출력→chat 근거 구간까지 역추적(API 경로=Cypher) |
| 수정 항목 | ai_need만 | ai_need + **lead_org**(후보→규칙→섀도 검증→게시→새 요청 적용까지 1회) + 근거가 있는 feasibility 체인 |
| X08 | API·worker 재시작 diff 0 | 동일(+collector, 위반 규칙 tenant worker 재시작) + 브라우저 새로고침 후 검증 카드를 서버 조회로 확인 |
| 규칙 검증용 긴급도 규칙 | urgency 긴급→판단 보류 규칙을 만들어 근거 체인에 사용 | FIX-S 이후 이 규칙은 거절되므로 **근거 체인을 feasibility(`정보 부족`→`조건부 가능`, 더 엄격한 허용 값)로 대체** |

### 발견 결함과 조치

| # | 구분 | 내용 | 조치 |
| --- | --- | --- | --- |
| F10 | **결함(수정함)** | 판단 맵(`frontend/src/pages/JudgmentMap.tsx`)의 `load()`가 응답 순서를 보호하지 않아, 기준 변경 직후 이전 기준(무필터)의 느린 응답이 새 결과를 덮어써 화면이 필터와 다른 그래프(102노드/126연결)를 보이는 경합. `[X06] criteria filters` 시험이 간헐 실패(재현: 이번 ui2 1회) | 요청 순번 가드(`loadSeq`)로 최신 요청의 응답만 반영하는 최소 수정. 수정 후 같은 시험 3/3 통과, vitest 37 통과, `tsc --noEmit` 오류 없음 |
| F11 | 관찰 | 실제 Jev는 `lead_org` 출력에 EvidenceSpan 인용을 달지 않는다(feasibility·urgency 위주). 따라서 lead_org 수정 기록은 `evidence_span_ids=[]`이고 lead_org 규칙은 근거 원문까지 역추적되지 않는다(Correction.evidence_span_ids == CITES 대상, 둘 다 빈 목록으로 일치). 근거 원문 역추적은 인용이 있는 feasibility 체인으로 입증 | 제품 결함 아님(모델 동작). 보고만 |
| F12 | 관찰 | 텍스트 전용 요청의 chat EvidenceSpan은 문장 단위로 나뉘며 시험 라벨(` (feas-probe-0)` 같은 꼬리 문장)도 한 구간이 된다. 모델이 인용한 구간이 라벨 문장일 수 있다 | 보고만(시험 문장 설계 영향) |
| F13 | 환경 | 저장소에 이 작업 외 프로세스(예: journal collector pid 4921)가 남아 있다. 이 작업이 띄운 프로세스가 아니므로 종료하지 않음 | 보고만 |

### 시험 설계상 정정·실패 이력(숨기지 않음)

- X04 `ValidationRun (POST==GET==DB)` 첫 시도 실패: F6 id 분리 이후에도 Run을 ValidationRun id로 조회하던 낡은 시험 코드 → `HAS_SHADOW_RUN` 관계로 정정(코드), 같은 이름으로 재시험 통과.
- X04 `monitoring SLO/summary … unchanged` 첫 시도 실패: SLO 창 시각이 호출마다 달라지는 무의미한 비교(이전 실행과 같은 사유) → 수집기를 켠 `shadow_monitoring` 재시험 2건 통과(`_mon_stable`로 창 시각 제외).
- X05 `invariant-weakening … refused; no RuleVersion/Config created` 실패: FIX-S 이후 후보 저장 자체가 422라 옛 시험의 모양(후보 저장 성공→버전 단계 거절)이 낡음 → F4 항목 4건으로 대체.
- X01 `lead_org corrections … spans are chat sentences` 실패: lead_org에는 모델 인용이 없는데 span을 요구한 잘못된 기대 → `(retest)` 항목으로 정정.
- EVID 첫 시도 실패(너무 엄격한 부분집합 조건: 요청 맵에는 규칙의 지지 수정 근거 구간도 포함) → 기대 정정 후 통과.
- X07 진행 중 실행 첫 시도 실패(중단이 Run Config 고정 전에 들어감, 이전 실행과 같은 사유) → `inflight` 재시험 통과.
- 브라우저: ui1 `[X01][X02]`(자료 부족 후보가 이미 승인된 상태라 옛 문구 기대 → 시험 갱신), ui1 `[X06]` 2회(`state.trace.chain`에 `source` 값이 섞여 있던 시험 데이터·`trace.span` 누락 → 정정), r1 `[EVID][X06]`(근거 구간이 '묶음' 노드로 접혀 있어 펼친 뒤 비교하도록 정정), ui2 `[X06] criteria filters`(F10), ui2/ui3 `[X08] map`(스냅샷 파일 순서·재시작 후 새 요청이 규칙 연결 수를 늘리는 것 → 재시작 후 새 요청 포함 스냅샷 `post2`로 비교하고 `diff_new_traffic` 항목이 '저장 상태 불변·그래프 차이는 새 요청 노드뿐'을 따로 검증). 모두 같은 제목으로 재실행해 통과(`ui-results.jsonl` 이력 보존).

### 이번에 별도 시험하지 않은 수정 항목

- FIX-SSE(공유 폴링)·FIX-R(재분석 경계)·FIX-C 중 로그인 경합은 이 시나리오에서 직접 대조하지 않았다. 회귀(`make test`·`test-acceptance`) 통과로만 확인.

### 남은 제한

- 모든 분류는 실제 Jev(`mode=live`, 판단 39건 전부)이지만 같은 문장 템플릿이라 판단이 비슷하다. 다양한 입력에서의 규칙 효과는 범위 밖이다.
- X09: 표본 충분 시 `개선 확인` 등 판정 경로는 이 시나리오(전 몇 건·후 몇 건 < 최소 20)에서 발생하지 않아 T35 통합 시험(알려진 표본)에 의존한다. 표본 부족 `관찰 중` 경로만 시험했다.
- lead_org 규칙은 근거 원문까지의 역추적 체인이 없다(F11). 근거 체인은 feasibility 규칙으로 입증했다.
- 위반 규칙의 `blocked_by_invariant` 적용 시험은 API로는 만들 수 없는 상태를 DB에 직접 써서 만든 별도 tenant(`<tenant>i`)에서 수행했고, 본 tenant의 데이터에는 영향이 없다.


## 6. 재현 방법

```sh
make up
cd backend
.venv/bin/python tests/acceptance/extension/provision_tenant.py <tenant>
WORKER: .venv/bin/python -m jevtriage.jobs.worker --tenant <tenant>   # API: uvicorn jevtriage.main:app --port <port>
export X38_OUT=<artifacts/validation/<ts>/extension> X38_TENANT=<tenant> X38_API=http://127.0.0.1:<port>
.venv/bin/python -m tests.acceptance.extension.scenario_r seed corrections rules apply invariants trace_detail insufficient chain_lead lead_retest chain_evidence evidence_layer graph f7 insufficient_ui_setup
(export ui1/r1 → playwright ui1 + extension-r r1 → insufficient_ui_verify reject lifecycle inflight shadow_monitoring → export ui2 → ui2 → snapshot pre → API/worker/collector 재시작 → snapshot post → diff post_restart → snapshot post2 diff_new_traffic → export ui3 → ui3(X38_SNAP=post2)+r3 → f6 playback dbsummary)
X38_SUFFIX=ui1 .venv/bin/python -m tests.acceptance.extension.scenario export   # then: cd ../frontend && X38_PHASE=ui1 npx playwright test -c playwright.extension.config.ts
... snapshot (pre) → 프로세스 재시작 → snapshot (post) → diff → ui3 ...
.venv/bin/python -m tests.acceptance.extension.report
```
