# T38 확장 연결 시나리오 검증 — X01–X10 판정

- 실행 tenant: `t-x38-10031834` (전용, worker는 `--tenant` 제한), 결과 디렉터리: `/Users/psw/Projects/decision-chat-bot/artifacts/validation/20261003T093618Z/extension`
- Jev: `JEV_MODE=live` (실제 모델 호출, 모든 판단 `mode=live`). 저장소: 공유 Neo4j(정지하지 않음). 데이터 디렉터리(journal/원본 파일)는 이 작업 전용 경로.
- 이 보고는 **확장 게이트 X01–X10**만 판정한다. 기존 게이트(G01–G12)는 4절 'X10 회귀'의 '기존 게이트 별도 보고' 표에서 재실행 결과로만 다루며, G 판정 자체는 T27 소관이다.

## 1. 판정 요약

| 게이트 | 판정 | 근거 요약 |
| --- | --- | --- |
| X01 | **통과** | API/DB 검사 3건 통과, 브라우저 검사 1건 통과 |
| X02 | **통과** | API/DB 검사 4건 통과, 브라우저 검사 1건 통과 |
| X03 | **통과** | API/DB 검사 8건 통과, 브라우저 검사 2건 통과 |
| X04 | **통과** | 섀도 검증 6회(규칙 버전 4종) 전후 보호 노드 8종 해시·active_run_id 포인터·SLO 분모·알림 동일, 저널 run_kind=shadow, ValidationRun 조건·표본 수 = API = DB = 화면. 첫 모니터링 비교는 무의미(수집기 중지)라 재시험 |
| X05 | **통과 (Trace 화면 한계 있음)** | 범위 내 3건 used(불필요→필요)·범위 밖 2건 out_of_scope·약화 규칙 2종 422 거절, APPLIED=Judgment API=Trace 단계 ID/Config/판단 값 대조. 한계 F3: Trace 단계 상세가 규칙 버전·전후 값을 표시하지 않음(판단 API·판단 맵에서 확인) |
| X06 | **통과** | API/DB 검사 9건 통과, 브라우저 검사 3건 통과 |
| X07 | **통과** | API/DB 검사 4건 통과, 브라우저 검사 2건 통과 |
| X08 | **통과** | API/DB 검사 2건 통과, 브라우저 검사 5건 통과 |
| X09 | **통과 (표본 부족 경로만 시험)** | 효과 API 표본·변경·수정·검토·실패 수 = DB 독립 계산 = 화면, 전 8건/후 <20건이라 `관찰 중·표본 부족`(미확정) 표시. 표본 충분 시 판정 경로는 T35 통합 시험에 의존 |
| X10 | **통과** | 백엔드 전체 129 통과·1 건너뜀(live 전용), 프런트 vitest 34 통과, 지정 회귀 시험 60 통과, 재생 무부작용 실측 통과 |

## 2. 10단계 실제 ID 표

| 단계 | 항목 | 실제 ID / 값 |
| --- | --- | --- |
| 1 | 접수·판단 요청(8건, AI 원안 ai_need=`불필요`) | `req_3db17b262a1546fdb070e52cc03ebc2b`, `req_9f6bbe87d6d74d198cf48c5ec4bfceaa`, `req_3d34e25aee2f457da1abf7d5c9864ad7`, `req_485f383761e34da2b7d1a4aa334d7e9e`, `req_35e51ef4e7094ab7b436eb3fa92b4308`, `req_96562009f5aa47f199ab51abaeaed935`, `req_a621234edfa84a52841609fb51a14bff`, `req_fb0bebc2ebe740c5902855dec3c4f7c5` |
| 1 | 같은 방향 수정 3건(→`필요`) | `req_a621234edfa84a52841609fb51a14bff`→`cor_82a6c2512ed649a8a3a48e82affb9e16`, `req_fb0bebc2ebe740c5902855dec3c4f7c5`→`cor_8145d2c72e3a4221b2e1564ec7ef3c58`, `req_96562009f5aa47f199ab51abaeaed935`→`cor_f00d744948d347d5a711f208ca08f2d6` |
| 1 | 반례 1건(수정 없이 승인) | `req_35e51ef4e7094ab7b436eb3fa92b4308` |
| 1 | 다른 방향 수정 2건(→`혼합`) | `req_485f383761e34da2b7d1a4aa334d7e9e`→`cor_1a4435c4bbe4443bb4824d182bad736b`, `req_3d34e25aee2f457da1abf7d5c9864ad7`→`cor_aacb1eb8f9ce4a36ac817912a0eb986d` |
| 3 | 후보(지지 3, 제안) / 후보(지지 2, 자료 부족) | `cand_8fcc507094e6868374ddec5c` / `cand_e123faef72028b6d12635bef` |
| 4 | 범위 수정 승인 결정 / 규칙 버전 / 기반 Config | `rdec_b9981756b1e342278df9ee206130ae59` / `R-AI_NEED-01@1` / v1 |
| 5 | 섀도 검증 / 게시 Config | `val_14d2a9f8539a45e6bd94c3a88b748b64` / v2 |
| 6 | 범위 내 새 요청(사용) | `req_fbf46be518bb408ca1ea51c221905c01` run `run_86c22cde53de4e72b7b352d94274ed21` step `step_b33142426994465cacba22c2c69ec588` 불필요→필요 |
| 6 | 범위 내 새 요청(사용) | `req_7079ab1620a24594b61f8c8ee624bd2c` run `run_13310066bb7a498883cae4eeb36df04a` step `step_19e32c1ebead4412884b8049e2da7b76` 불필요→필요 |
| 6 | 범위 내 새 요청(사용) | `req_fda7656727934b249a0f71f560c8e613` run `run_bbaa3b9225924c479ceabcd119ea5356` step `step_d8c89785f2674d00bd4b54fc803c9766` 불필요→필요 |
| 6 | 범위 밖 새 요청(미사용 기록) | `req_f7a2cacdb0904be78b7f38250d0d54bd` run `run_cf0c6ad86f0b4ff59072d11f1bd3d93e` step `step_fd7d487ed2934616928b580481f8a11f` 불필요 유지 |
| 7 | 근거 있는 2번째 규칙(긴급도) 후보/결정/버전/Config | `cand_861307de943efe054b1e407e` / `rdec_ae5e2330872a441ea3fb562b5c28eaf8` / `R-URGENCY-01@1` / v3 |
| 7 | 역추적 사슬 | step `step_8cf44754bbaa4438ac327e03334fb7c4` → `R-URGENCY-01@1` → `rdec_ae5e2330872a441ea3fb562b5c28eaf8` → `cand_861307de943efe054b1e407e` → `cor_3ed68e6a980e4aacba33b94e29d7f632` → `mout_45caafb4e2f64ebdb7ddb99a4d50a2ca` → `esp_65cd3dfb4cac406091de5cd3017d295c` |
| 8 | 중단/ v2 게시 / 되돌리기 Config | v4 / v5 / v6 (v2=`R-AI_NEED-01@2`) |
| 8 | 진행 중 / 중단 후 / v2 / 되돌린 뒤 요청 | `req_1653c8a6a84a465f929389a2939b96ff` / `req_160dcd95728641b7ba2c41c7a01fb254` / `req_5d24648202a04d01b7c96729503c9de2` / `req_93a9da07d6ec433ea912c76e2f2333f4` |
| 9 | 재시작 후 새 요청 | `req_bd8a4c33748849238d8e6029b8ced18a` run `run_9878dea304e34c49b40f29298505d4b6` |

## 3. 게이트별 증거 (최신 결과 + 재시험 이력)

### X01 — 통과

- [통과] review decisions submitted
  - 증거: `{"plan": {"same_direction": ["req_a621234edfa84a52841609fb51a14bff", "req_fb0bebc2ebe740c5902855dec3c4f7c5", "req_96562009f5aa47f199ab51abaeaed935"], "counter": "req_35e51ef4e7094ab7b436eb3fa92b4308", "other_direction": ["req_485f383761e34da2b7d1a4aa334d7e9e", "req_3d34e25aee2f457da1abf7d5c9864ad7"]}, "original": "불필요", "dir_y": "필요", "dir_z": "혼합"}`
- [**실패**] DB Correction == API(/requests/{id}/corrections, /learning/corrections); AI original kept; CORRECTS->ModelOutput — _재시험으로 대체: 같은 항목을 수정·재실행해 통과(시험 코드 정정 후, 아래 이력 참조)_
  - 증거: `{"corrections": {"req_a621234edfa84a52841609fb51a14bff": {"correction_id": "cor_82a6c2512ed649a8a3a48e82affb9e16", "review_id": "rvw_9da72a2138bb47e5aaf7fe53fd50d252", "run_id": "run_dfbff2f5b2624464b2b403f64bbcb5f1", "revision_id": "rev_1b79c32b807c4cbfb428493e0aaf611d", "config_version": 1, "ai_value": "\"불필요\"", "corrected_value": "\"필요\"", "corrected_by": "usr_t-x38-10031834_reviewer", "corrected_at": "2026-10-03T09:36:57.341000000+00:00", "reason": "T38: ai_need 같은 방향 수정", "evidence_span_ids": [], "checks": {"id": true, "ai_value": true, "corrected_value": true, "reason": true, "corrected_by": true, "corrected_at": true, "revision_id": true, "run_id": true, "config_version": true, "list…`
- [통과] DB Correction == API(/requests/{id}/corrections, /learning/corrections); AI original kept; CORRECTS->ModelOutput
  - 증거: `{"corrections": {"req_a621234edfa84a52841609fb51a14bff": {"correction_id": "cor_82a6c2512ed649a8a3a48e82affb9e16", "review_id": "rvw_9da72a2138bb47e5aaf7fe53fd50d252", "run_id": "run_dfbff2f5b2624464b2b403f64bbcb5f1", "revision_id": "rev_1b79c32b807c4cbfb428493e0aaf611d", "config_version": 1, "ai_value": "\"불필요\"", "corrected_value": "\"필요\"", "corrected_by": "usr_t-x38-10031834_reviewer", "corrected_at": "2026-10-03T09:36:57.341000000+00:00", "reason": "T38: ai_need 같은 방향 수정", "evidence_span_ids": [], "checks": {"id": true, "ai_value": true, "corrected_value": true, "reason": true, "corrected_by": true, "corrected_at": true, "revision_id": true, "run_id": true, "config_version": true, "list…`
- [통과] corrections on cited outputs keep evidence span IDs (DB Correction.evidence_span_ids == CITES targets of the corrected ModelOutput)
  - 증거: `{"urgency_original": {}, "target": "판단 보류", "corrections": {"cor_b883b34442f34569bce57d37248bbd8f": {"request": "req_245250b0119d49818ea62ce51724f863", "spans": ["esp_d2376c22cea44767a00d3e7b2b8b9ff7"]}, "cor_3ed68e6a980e4aacba33b94e29d7f632": {"request": "req_957a2ff6918040bb9082bdb10a305065", "spans": ["esp_65cd3dfb4cac406091de5cd3017d295c"]}, "cor_2053d3d03a044b54809204dcf9074c80": {"request": "req_f4e911dcb56547869d7263a1b928d09c", "spans": ["esp_f78a8b8bc3d44475b2df71048917e521"]}}}`
- [브라우저 ui1: 통과] [X01][X02] reviewer sees AI original vs correction with who/when/revision/run/Config, support & counter examples, 자료 부족
  - 화면 값: `[{"candidate": "cand_8fcc507094e6868374ddec5c", "support_rows": [{"request": "req_a621234edfa84a52841609fb51a14bff", "correction": "cor_82a6c2512ed649a8a3a48e82affb9e16", "run": "run_dfbff2f5b2624464b2b403f64bbcb5f1", "revision": "rev_1b79c32b807c4cbfb428493e0aaf611d", "config": 1}, {"request": "req_fb0bebc2ebe740c5902855dec3c4f7c5", "correction": "cor_8145d2c72e3a4221b2e1564ec7ef3c58", "run": "run_ac3b864584c54ab7b8344b5238624a7f", "revision": "rev_20c1346355a848a4aad995afe24f684b", "config": 1…`

### X02 — 통과

- [통과] candidate (3 same direction) linked to Correction IDs with counter/scope/uncertainty
  - 증거: `{"generate_status": 200, "candidate": {"id": "cand_8fcc507094e6868374ddec5c", "field": "ai_need", "status": "제안", "support_ids": ["cor_8145d2c72e3a4221b2e1564ec7ef3c58", "cor_82a6c2512ed649a8a3a48e82affb9e16", "cor_f00d744948d347d5a711f208ca08f2d6"], "counter_ids": ["rdec_3dc2882fea434393b0b6bf97897526d9", "rdec_80d15e9e652c47ac90a8aa675b6c2618", "rdec_c6e4b97fc8724c719141ac81b7226aef"], "api_support_ids": ["cor_8145d2c72e3a4221b2e1564ec7ef3c58", "cor_82a6c2512ed649a8a3a48e82affb9e16", "cor_f00d744948d347d5a711f208ca08f2d6"], "scope": {"all": [{"field": "ai_need", "op": "eq", "value": "불필요"}, {"field": "feasibility", "op": "eq", "value": "정보 부족"}, {"field": "lead_org", "op": "eq", "value": "…`
- [통과] other direction with 2 corrections is '자료 부족' (DB==API)
  - 증거: `{"candidate": {"id": "cand_e123faef72028b6d12635bef", "field": "ai_need", "status": "자료 부족", "support_ids": ["cor_1a4435c4bbe4443bb4824d182bad736b", "cor_aacb1eb8f9ce4a36ac817912a0eb986d"], "counter_ids": ["rdec_24fc67ffdcd7422684754a53bc498c8d", "rdec_80d15e9e652c47ac90a8aa675b6c2618", "rdec_9abfa865fcdb48beb5bc48960ad831ca", "rdec_dc33cefabbd14dae882fc97f6fa5d8ce"], "api_support_ids": ["cor_1a4435c4bbe4443bb4824d182bad736b", "cor_aacb1eb8f9ce4a36ac817912a0eb986d"], "scope": {"all": [{"field": "ai_need", "op": "eq", "value": "불필요"}, {"field": "feasibility", "op": "eq", "value": "정보 부족"}, {"field": "lead_org", "op": "eq", "value": "IT팀"}, {"op": "lte", "signal": "ai_team_involvement", "value…`
- [통과] candidate generation did not change Config
  - 증거: `{"config_version": 1}`
- [통과] candidate (3 same direction) linked to Correction IDs with counter/scope/uncertainty
  - 증거: `{"generate_status": 200, "candidate": {"id": "cand_8fcc507094e6868374ddec5c", "field": "ai_need", "status": "제안", "support_ids": ["cor_8145d2c72e3a4221b2e1564ec7ef3c58", "cor_82a6c2512ed649a8a3a48e82affb9e16", "cor_f00d744948d347d5a711f208ca08f2d6"], "counter_ids": ["rdec_3dc2882fea434393b0b6bf97897526d9", "rdec_80d15e9e652c47ac90a8aa675b6c2618", "rdec_c6e4b97fc8724c719141ac81b7226aef"], "api_support_ids": ["cor_8145d2c72e3a4221b2e1564ec7ef3c58", "cor_82a6c2512ed649a8a3a48e82affb9e16", "cor_f00d744948d347d5a711f208ca08f2d6"], "scope": {"all": [{"field": "ai_need", "op": "eq", "value": "불필요"}, {"field": "feasibility", "op": "eq", "value": "정보 부족"}, {"field": "lead_org", "op": "eq", "value": "…`
- [통과] other direction with 2 corrections is '자료 부족' (DB==API)
  - 증거: `{"candidate": {"id": "cand_e123faef72028b6d12635bef", "field": "ai_need", "status": "자료 부족", "support_ids": ["cor_1a4435c4bbe4443bb4824d182bad736b", "cor_aacb1eb8f9ce4a36ac817912a0eb986d"], "counter_ids": ["rdec_24fc67ffdcd7422684754a53bc498c8d", "rdec_80d15e9e652c47ac90a8aa675b6c2618", "rdec_9abfa865fcdb48beb5bc48960ad831ca", "rdec_dc33cefabbd14dae882fc97f6fa5d8ce"], "api_support_ids": ["cor_1a4435c4bbe4443bb4824d182bad736b", "cor_aacb1eb8f9ce4a36ac817912a0eb986d"], "scope": {"all": [{"field": "ai_need", "op": "eq", "value": "불필요"}, {"field": "feasibility", "op": "eq", "value": "정보 부족"}, {"field": "lead_org", "op": "eq", "value": "IT팀"}, {"op": "lte", "signal": "ai_team_involvement", "value…`
- [통과] candidate generation did not change Config
  - 증거: `{"config_version": 1}`
- [통과] evidence-backed candidate (urgency→긴급): support == the 3 Correction IDs with cited spans, scope/uncertainty present
  - 증거: `{"candidate": "cand_861307de943efe054b1e407e", "status": "제안", "support": ["cor_2053d3d03a044b54809204dcf9074c80", "cor_3ed68e6a980e4aacba33b94e29d7f632", "cor_b883b34442f34569bce57d37248bbd8f"], "counter_count": 1, "scope_predicates": 10, "uncertainty": {"counter_count": 1, "minimum_support": 3, "organization_count": 3, "single_organization_bias": false, "support_count": 3}}`
- [브라우저 ui1: 통과] [X01][X02] reviewer sees AI original vs correction with who/when/revision/run/Config, support & counter examples, 자료 부족
  - 화면 값: `[{"candidate": "cand_8fcc507094e6868374ddec5c", "support_rows": [{"request": "req_a621234edfa84a52841609fb51a14bff", "correction": "cor_82a6c2512ed649a8a3a48e82affb9e16", "run": "run_dfbff2f5b2624464b2b403f64bbcb5f1", "revision": "rev_1b79c32b807c4cbfb428493e0aaf611d", "config": 1}, {"request": "req_fb0bebc2ebe740c5902855dec3c4f7c5", "correction": "cor_8145d2c72e3a4221b2e1564ec7ef3c58", "run": "run_ac3b864584c54ab7b8344b5238624a7f", "revision": "rev_20c1346355a848a4aad995afe24f684b", "config": 1…`

### X03 — 통과

- [통과] all non-rule_admin roles get 403 on decision/scope-change/reject/version/validate/mark-validated/publish/stop/revert
  - 증거: `{"status_by_role": {"requester": {"decision": 403, "decision_scope_change": 403, "reject": 403, "create_version": 403, "validate": 403, "mark_validated": 403, "publish": 403, "stop": 403, "revert": 403}, "reviewer": {"decision": 403, "decision_scope_change": 403, "reject": 403, "create_version": 403, "validate": 403, "mark_validated": 403, "publish": 403, "stop": 403, "revert": 403}, "team_member": {"decision": 403, "decision_scope_change": 403, "reject": 403, "create_version": 403, "validate": 403, "mark_validated": 403, "publish": 403, "stop": 403, "revert": 403}, "operator": {"decision": 403, "decision_scope_change": 403, "reject": 403, "create_version": 403, "validate": 403, "mark_valida…`
- [**실패**] policy_editor cannot publish a rules diff via /api/policy/publish — _재시험으로 대체: probe used an invalid rule id (R-AI-NEED-01); retested with a valid id_
  - 증거: `{"status": 422, "body": "{\"detail\":{\"code\":\"SCHEMA_INVALID\",\"reason\":\"Value error, invalid rule identity\"}}"}`
- [통과] rejected calls left candidate/decision/version/config state unchanged
  - 증거: `{"before": {"RuleCandidate": {"count": 2, "sha256": "14fd7049623a6982"}, "RuleDecision": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "RuleVersion": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "ConfigVersion": {"count": 1, "sha256": "6ffc947be1287465"}}, "after": {"RuleCandidate": {"count": 2, "sha256": "14fd7049623a6982"}, "RuleDecision": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "RuleVersion": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "ConfigVersion": {"count": 1, "sha256": "6ffc947be1287465"}}}`
- [통과] single review approval (API) changed no RuleCandidate/RuleDecision/RuleVersion/ConfigVersion
  - 증거: `{"review_id": "rvw_3e266286fe64426195517a32a1f3b46c", "request_id": "req_3db17b262a1546fdb070e52cc03ebc2b", "state": {"RuleCandidate": {"count": 2, "sha256": "14fd7049623a6982"}, "RuleDecision": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "RuleVersion": {"count": 0, "sha256": "4f53cda18c2baa0c"}, "ConfigVersion": {"count": 1, "sha256": "6ffc947be1287465"}}, "active_config": 1}`
- [통과] rule_admin scope-change approval: confirmed scope stored (differs from proposal), candidate approved
  - 증거: `{"decision_id": "rdec_b9981756b1e342278df9ee206130ae59", "confirmed_scope": {"all": [{"field": "ai_need", "op": "eq", "value": "불필요"}, {"field": "lead_org", "op": "eq", "value": "IT팀"}, {"op": "lte", "signal": "clinical_safety", "value": 0.5}, {"op": "lte", "signal": "regulatory", "value": 0.5}]}, "proposed_scope_predicates": 10, "db": {"action": "approve_with_scope_change", "by": "usr_t-x38-10031834_rule_admin", "candidate_status": "approved"}}`
- [통과] policy_editor cannot publish a rules diff via /api/policy/publish (retest with a valid rule id)
  - 증거: `{"status": 422, "body": "{\"detail\":{\"code\":\"RULE_ADMIN_REQUIRED\",\"reason\":\"rules 변경은 rule_admin 전용 경로에서만 허용됩니다.\"}}"}`
- [통과] rule_admin scope-change approval: confirmed scope stored (differs from proposal), candidate approved
  - 증거: `{"decision_id": "rdec_b9981756b1e342278df9ee206130ae59", "confirmed_scope": {"all": [{"field": "ai_need", "op": "eq", "value": "불필요"}, {"field": "lead_org", "op": "eq", "value": "IT팀"}, {"op": "lte", "signal": "clinical_safety", "value": 0.5}, {"op": "lte", "signal": "regulatory", "value": 0.5}]}, "proposed_scope_predicates": 10, "db": {"action": "approve_with_scope_change", "by": "usr_t-x38-10031834_rule_admin", "candidate_status": "approved"}}`
- [통과] publish before validation is refused (409) and Config version unchanged
  - 증거: `{"status": 409, "body": "{\"detail\":{\"code\":\"INVALID_TRANSITION\",\"reason\":\"게시 가능한 검증 상태가 아닙니다.\"}}", "active_config": 1}`
- [통과] validated rule published as new Config version (rule in active rules, PUBLISHED_IN), audit + rule.* events recorded
  - 증거: `{"config_version": 2, "prior": 1, "active_rules": ["R-AI_NEED-01@1"], "audit": {"RuleCandidate:cand_8fcc507094e6868374ddec5c": [["rule.decision", "usr_t-x38-10031834_rule_admin", "T38: 범위를 임상·규제 신호 낮음으로 확정"]], "RuleVersion:R-AI_NEED-01@1": [["rule.version_created", "usr_t-x38-10031834_rule_admin", "T38: 규칙 버전 생성"], ["rule.validated", "usr_t-x38-10031834_rule_admin", "T38: 부작용 0건 확인"]], "ConfigVersion:2": [["rule.publish", "usr_t-x38-10031834_rule_admin", "T38: 게시"]]}, "events": [{"kind": "rule.decision", "n": 1}, {"kind": "rule.publish", "n": 1}, {"kind": "rule.validated", "n": 1}, {"kind": "rule.version_created", "n": 1}]}`
- [통과] rule_admin rejects a candidate: decision+audit recorded, status rejected; approval after rejection and version creation refused; no RuleVersion/Config change
  - 증거: `{"candidate": "cand_3251e2c1a26edd1fedc060d9", "reject": 200, "approve_after_reject": [409, "{\"detail\":{\"code\":\"CANDIDATE_REJECTED\",\"reason\":\"기각된 후보입니다.\"}}"], "create_version_after_reject": [409, "{\"detail\":{\"code\":\"CANDIDATE_REJECTED\",\"reason\":\"기각된 후보에서 규칙을 만들 수 없습니다.\"}}"], "db": [{"a": "reject", "by": "usr_t-x38-10031834_rule_admin", "r": "T38: 근거 부족으로 기각", "s": "rejected"}], "audit": [["rule.decision", "usr_t-x38-10031834_rule_admin", "T38: 근거 부족으로 기각"]]}`
- [브라우저 ui1: 통과] [X03] requester has no access to rule learning; no rule actions exposed
- [브라우저 ui1: 통과] [X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족
  - 화면 값: `[{"ui_used": 3, "ui_out": 6, "db": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0}, "after": {"sample_count": 9, "corrections": 3, "review_transitions": 9, "failures": 0, "classification_changes": 3}, "used": {"sample_count": 3, "corrections": 0, "review_transitions": 3, "failures": 0, "classification_changes": 3}, "out_of_scope": {"sample_count": 6, "corrections": 3, "review_transitions": 6, "failures": 0, "classification_cha…`

### X04 — 통과

- [통과] protected nodes (Task/Assignment/Review/ReviewDecision/Event/Request/Judgment/Correction) identical before/after shadow
  - 증거: `{"before": {"Task": {"count": 7, "sha256": "dd897ccf55536ca8"}, "Assignment": {"count": 7, "sha256": "3841469efb3dab33"}, "Review": {"count": 8, "sha256": "eec607f2a66efe77"}, "ReviewDecision": {"count": 7, "sha256": "1760f5720d2020aa"}, "Event": {"count": 129, "sha256": "4ed4e9022e77acd9"}, "Request": {"count": 8, "sha256": "6872759db40b9b74"}, "Judgment": {"count": 8, "sha256": "3d150acd19f440b5"}, "Correction": {"count": 5, "sha256": "2f14bff1a31f6b51"}}, "after": {"Task": {"count": 7, "sha256": "dd897ccf55536ca8"}, "Assignment": {"count": 7, "sha256": "3841469efb3dab33"}, "Review": {"count": 8, "sha256": "eec607f2a66efe77"}, "ReviewDecision": {"count": 7, "sha256": "1760f5720d2020aa"}, "…`
- [통과] counts and Request.active_run_id pointers identical before/after shadow
  - 증거: `{"before": {"Task": 7, "Assignment": 7, "Review": 8, "Event": 129, "Notification": 0, "ReviewDecision": 7, "Judgment": 8, "Request": 8, "active_run_pointers": {"n": 8, "ptr": ["req_35e51ef4e7094ab7b436eb3fa92b4308=run_c067972d6cdd40c2a18cbc529c1c185a", "req_3d34e25aee2f457da1abf7d5c9864ad7=run_fdf5081bd1af4c93a6365bccc6f58ef6", "req_3db17b262a1546fdb070e52cc03ebc2b=run_99d58c815d794f18b9440608e276a3ee", "req_485f383761e34da2b7d1a4aa334d7e9e=run_1af75dc9f7434fc199444c19ecef99ec", "req_96562009f5aa47f199ab51abaeaed935=run_9c254957bedb4cb197f9b8ff7d4bb40c", "req_9f6bbe87d6d74d198cf48c5ec4bfceaa=run_bce2ccfcbce44b719d5821c0d3c6f546", "req_a621234edfa84a52841609fb51a14bff=run_dfbff2f5b2624464b2b4…`
- [**실패**] monitoring SLO/summary denominators and alerts unchanged by shadow — _재시험으로 대체: first attempt was vacuous (collector stopped, clock-dependent window); retested with collector running_
  - 증거: `{"before": "08710f1f3dabb7e6", "after": "c89b536d1c4461c1", "summary_after": {"summary": {"availability": {"valid_calls": 0, "successful_calls": 0, "failed_calls": 0, "pending_calls": 0, "unknown_validity": 0, "ratio": null}, "judgment": {"eligible_requests": 0, "within_120s": 0, "failed_120s": 0, "pending_120s": 0, "ratio": null, "candidate_commits": 0, "failed_runs": 0, "late_recoveries": 0, "unconfirmed_samples": 0}, "latency_ms": {"intake_p95": null, "text_first_p95": null, "attachment_first_p95": null, "sse_deliver_p95": null, "revision_p95": null, "step_p95": null}, "requests": {"received": 0, "failed_before_id": 0}, "file_exclusions": 0, "first_eligible_after_file_decision": 0, "cance…`
- [통과] ValidationRun (POST result == GET API == DB): conditions, sample counts, side_effects=0, run_kind=shadow
  - 증거: `{"validation_id": "val_14d2a9f8539a45e6bd94c3a88b748b64", "sample_count": 8, "labeled_count": 7, "changed_count": 8, "changes_by_value": {"ai_need:필요": 8}, "base": 1, "candidate": "1+R-AI_NEED-01@1", "human_correction_needed_base/candidate": [5, 4], "window": ["2026-01-01T00:00:00+00:00", "2026-12-31T00:00:00+00:00"], "shadow_run_kind": [{"kind": "shadow", "status": "completed"}], "field_equal": {"sample_count": true, "labeled_count": true, "changed_count": true, "side_effects": true, "status": true, "run_kind": true, "base_config_version": true, "candidate_config_version": true, "max_calls": true, "calls": true, "human_correction_needed_base": true, "human_correction_needed_candidate": true…`
- [미검증/정정] (정정) 'monitoring SLO/summary … unchanged' FAIL: 최초 시도는 SLO 창 시각이 호출마다 달라지고 수집기 미기동으로 값이 전부 0이어서 무의미 — 별도 시험(shadow_monitoring)으로 재수행
  - 증거: `{"cause": "window_start/window_end drift, collector stopped"}`
- [통과] second rule validated by shadow: side_effects=0, status completed, sample counts recorded
  - 증거: `{"id": "val_ebc6fbf10d634862b9eae78b566dceb2", "sample_count": 16, "labeled_count": 11, "changed_count": 4, "side_effects": 0, "status": "completed", "calls": 0}`
- [**실패**] (retest, collector running, non-vacuous) SLO/summary denominators and alerts unchanged by shadow; shadow counted only in shadow_runs — _재시험으로 대체: summary.kinds.shadow_validation +1 (shadow-only counter) was compared too; retest 2 excludes shadow-only fields_
  - 증거: `{"nonzero_denominators": {"valid_calls": 22, "requests_received": 14, "eligible_requests": 14}, "shadow_runs": [2, 3], "before_hash": "e377a95d2964d1ec", "after_hash": "904b61916473e149", "validation": "val_2471af6ce59c452791b37f51e2b2465c", "side_effects": 0}`
- [통과] (retest) protected nodes and active_run_id pointers identical across the second shadow validation
  - 증거: `{"protected": {"Task": {"count": 19, "sha256": "b22d7cccc0dcf649"}, "Assignment": {"count": 11, "sha256": "fab842d3e3831f18"}, "Review": {"count": 22, "sha256": "017ccb21e7a994cb"}, "ReviewDecision": {"count": 11, "sha256": "bb013e6f92306f4b"}, "Event": {"count": 360, "sha256": "6daafa4607b3a75c"}, "Request": {"count": 22, "sha256": "d489f2ef21003b7d"}, "Judgment": {"count": 22, "sha256": "418c7e41635145f5"}, "Correction": {"count": 8, "sha256": "6047629d4154f664"}}, "pointers": 22}`
- [통과] journal records the shadow validation with run_kind='shadow'
  - 증거: `{"journal_rows": [{"kind": "shadow_validation", "run_kind": "shadow"}]}`
- [**실패**] (retest, collector running, non-vacuous) SLO/summary denominators and alerts unchanged by shadow; shadow counted only in shadow_runs — _재시험으로 대체: summary.kinds.shadow_validation +1 (shadow-only counter) was compared too; retest 2 excludes shadow-only fields_
  - 증거: `{"nonzero_denominators": {"valid_calls": 22, "requests_received": 14, "eligible_requests": 14}, "shadow_runs": [3, 4], "before_hash": "904b61916473e149", "after_hash": "f2cc37a712ba7b2c", "validation": "val_150e1740ba754061b0e978f34c0a2c5a", "side_effects": 0, "diff": [{"path": "/summary/kinds/shadow_validation", "before": 3, "after": 4}]}`
- [통과] (retest) protected nodes and active_run_id pointers identical across the second shadow validation
  - 증거: `{"protected": {"Task": {"count": 19, "sha256": "b22d7cccc0dcf649"}, "Assignment": {"count": 11, "sha256": "fab842d3e3831f18"}, "Review": {"count": 22, "sha256": "017ccb21e7a994cb"}, "ReviewDecision": {"count": 11, "sha256": "bb013e6f92306f4b"}, "Event": {"count": 360, "sha256": "6daafa4607b3a75c"}, "Request": {"count": 22, "sha256": "d489f2ef21003b7d"}, "Judgment": {"count": 22, "sha256": "418c7e41635145f5"}, "Correction": {"count": 8, "sha256": "6047629d4154f664"}}, "pointers": 22}`
- [통과] journal records the shadow validation with run_kind='shadow'
  - 증거: `{"journal_rows": [{"kind": "shadow_validation", "run_kind": "shadow"}]}`
- [통과] (retest 2: shadow-only fields excluded) SLO/summary denominators and alerts unchanged by shadow; shadow counted only in shadow_runs/kinds.shadow_validation
  - 증거: `{"nonzero_denominators": {"valid_calls": 22, "requests_received": 14, "eligible_requests": 14}, "shadow_runs": [4, 5], "before_hash": "d11ee4466d6c0c5c", "after_hash": "d11ee4466d6c0c5c", "validation": "val_51fe535c35b74e9296890dd1cfb5f2eb", "side_effects": 0, "diff": []}`
- [통과] (retest) protected nodes and active_run_id pointers identical across the second shadow validation
  - 증거: `{"protected": {"Task": {"count": 19, "sha256": "b22d7cccc0dcf649"}, "Assignment": {"count": 11, "sha256": "fab842d3e3831f18"}, "Review": {"count": 22, "sha256": "017ccb21e7a994cb"}, "ReviewDecision": {"count": 11, "sha256": "bb013e6f92306f4b"}, "Event": {"count": 360, "sha256": "6daafa4607b3a75c"}, "Request": {"count": 22, "sha256": "d489f2ef21003b7d"}, "Judgment": {"count": 22, "sha256": "418c7e41635145f5"}, "Correction": {"count": 8, "sha256": "6047629d4154f664"}}, "pointers": 22}`
- [통과] journal records the shadow validation with run_kind='shadow'
  - 증거: `{"journal_rows": [{"kind": "shadow_validation", "run_kind": "shadow"}]}`
- [브라우저 ui1: 통과] [X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족
  - 화면 값: `[{"ui_used": 3, "ui_out": 6, "db": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0}, "after": {"sample_count": 9, "corrections": 3, "review_transitions": 9, "failures": 0, "classification_changes": 3}, "used": {"sample_count": 3, "corrections": 0, "review_transitions": 3, "failures": 0, "classification_changes": 3}, "out_of_scope": {"sample_count": 6, "corrections": 3, "review_transitions": 6, "failures": 0, "classification_cha…`

### X05 — 통과 (Trace 화면 한계 있음)

- [통과] post-publish in-scope requests: rule used, result changed (불필요→필요), APPLIED(before/after/version) == Judgment API == Trace rule step, Config pinned
  - 증거: `{"config_version": 2, "rule": "R-AI_NEED-01@1", "requests": [{"kind": "in_scope", "run_id": "run_86c22cde53de4e72b7b352d94274ed21", "api_ai_need": "필요", "db_ai_need": "필요", "model_raw_ai_need": "불필요", "api_rule_effects": [{"rule_version": "R-AI_NEED-01@1", "effect": "rule", "outcome": "used", "before": "불필요", "after": "필요", "config_version": 2}], "db_applied": [{"step": "step_b33142426994465cacba22c2c69ec588", "kind": "rule", "rule": "R-AI_NEED-01@1", "outcome": "used", "before": "\"불필요\"", "after": "\"필요\"", "rv": "R-AI_NEED-01@1"}], "flow_config_version": 2, "flow_rule_steps": ["step_1a0d42d6f6374ea3bfd5382c14de98d5", "step_b33142426994465cacba22c2c69ec588"], "step_ids_in_applied": ["step_…`
- [통과] out-of-scope request: APPLIED out_of_scope recorded, classification NOT changed by the rule
  - 증거: `{"request": "req_f7a2cacdb0904be78b7f38250d0d54bd", "probe": {"kind": "out_of_scope_probe", "run_id": "run_cf0c6ad86f0b4ff59072d11f1bd3d93e", "api_ai_need": "불필요", "db_ai_need": "불필요", "model_raw_ai_need": "불필요", "api_rule_effects": [{"rule_version": "R-AI_NEED-01@1", "effect": "rule", "outcome": "out_of_scope", "before": "불필요", "after": "불필요", "config_version": 2}], "db_applied": [{"step": "step_fd7d487ed2934616928b580481f8a11f", "kind": "rule", "rule": "R-AI_NEED-01@1", "outcome": "out_of_scope", "before": "\"불필요\"", "after": "\"불필요\"", "rv": "R-AI_NEED-01@1"}], "flow_config_version": 2, "flow_rule_steps": ["step_3dfad9443abc4f1bb3d7740c3aadfd40", "step_fd7d487ed2934616928b580481f8a11f"], …`
- [통과] pre-publication runs have no APPLIED rows for the rule (and still have their rule step)
  - 증거: `{"seed_requests": 8, "applied_rows": 0, "runs_with_rule_step": 8}`
- [통과] invariant-weakening rules (feasibility→가능, urgency→일반) are refused; no RuleVersion/Config created
  - 증거: `{"attempts": [{"attempt": "feasibility→가능", "candidate_status": 404, "candidate_body": "{\"detail\":\"Correction not found\"}"}, {"attempt": "urgency→일반", "candidate_status": 404, "candidate_body": "{\"detail\":\"Correction not found\"}"}], "config_validation_errors": [{"code": "SCHEMA_INVALID", "reason": "Value error, rule weakens mandatory review or assignment safety"}], "state_before": {"RuleVersion": {"count": 1, "sha256": "9759e6d10a74a9c3"}, "ConfigVersion": {"count": 2, "sha256": "9a8035962587886c"}}, "state_after": {"RuleVersion": {"count": 1, "sha256": "9759e6d10a74a9c3"}, "ConfigVersion": {"count": 2, "sha256": "9a8035962587886c"}}}`
- [통과] invariant-weakening rules (feasibility→가능, urgency→일반) are refused; no RuleVersion/Config created
  - 증거: `{"attempts": [{"attempt": "feasibility→가능", "candidate_status": 201, "decision_status": 200, "version_status": 422, "version_body": "{\"detail\":{\"code\":\"RULE_INVALID\",\"reason\":\"rule weakens mandatory review or assignment safety\"}}"}, {"attempt": "urgency→일반", "candidate_status": 201, "decision_status": 200, "version_status": 422, "version_body": "{\"detail\":{\"code\":\"RULE_INVALID\",\"reason\":\"rule weakens mandatory review or assignment safety\"}}"}], "config_validation_errors": [{"code": "SCHEMA_INVALID", "reason": "Value error, rule weakens mandatory review or assignment safety"}], "state_before": {"RuleVersion": {"count": 1, "sha256": "9759e6d10a74a9c3"}, "ConfigVersion": {"c…`
- [미검증/정정] (정정) 'invariant-weakening … refused' 첫 PASS 판정은 무효: 후보 생성이 404/500으로 끝나 규칙 버전 검사에 도달하지 못함 — 이후 재시험 항목이 유효
  - 증거: `{"cause": "supporting_correction_ids field mismatch(404), then POST /api/learning/candidates 500 (async generator in any())"}`
- [통과] second rule (urgency): APPLIED rows for a new request == Judgment API rule_effects (both rules evaluated)
  - 증거: `{"request": "req_9163956b00194546bd0221bcbdd50ac9", "run": "run_efb9b2f49eae496f9b334a0138fcd7d2", "applied": [{"rule": "R-AI_NEED-01@1", "outcome": "out_of_scope", "b": "\"불필요\"", "a": "\"불필요\""}, {"rule": "R-URGENCY-01@1", "outcome": "used", "b": "\"긴급\"", "a": "\"판단 보류\""}], "api": [{"rule_version": "R-AI_NEED-01@1", "effect": "rule", "outcome": "out_of_scope", "before": "불필요", "after": "불필요", "config_version": 3}, {"rule_version": "R-URGENCY-01@1", "effect": "rule", "outcome": "used", "before": "긴급", "after": "판단 보류", "config_version": 3}], "urgency": "판단 보류"}`
- [브라우저 ui1: 통과] [X05] Trace: "규칙 적용" step of an in-scope run shows the stored judgment; out-of-scope run keeps the model value
  - 화면 값: `[{"used": {"request": "req_fbf46be518bb408ca1ea51c221905c01", "run": "run_86c22cde53de4e72b7b352d94274ed21", "step": "step_b33142426994465cacba22c2c69ec588", "shows_rule_version": false, "shows_before_after": false}, "out_of_scope": {"request": "req_f7a2cacdb0904be78b7f38250d0d54bd", "run": "run_cf0c6ad86f0b4ff59072d11f1bd3d93e", "step": "step_fd7d487ed2934616928b580481f8a11f", "shows_rule_version": false, "shows_before_after": false}}]`

### X06 — 통과

- [통과] graph API[request] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 44, "edge_count": 42, "layers": {"1": 31, "2": 2, "3": 7, "4": 2, "5": 2}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[run] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 44, "edge_count": 42, "layers": {"1": 31, "2": 2, "3": 7, "4": 2, "5": 2}, "missing_in_api": [], "extra_in_api": []}`
- [**실패**] graph API[rule_urgency] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers) — _재시험으로 대체: 같은 항목을 수정·재실행해 통과(시험 코드 정정 후, 아래 이력 참조)_
  - 증거: `{"node_count": 16, "edge_count": 15, "layers": {"1": 9, "2": 1, "3": 2, "4": 3, "5": 1}, "missing_in_api": [], "extra_in_api": []}`
- [**실패**] graph API[rule_ai_need] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers) — _재시험으로 대체: 같은 항목을 수정·재실행해 통과(시험 코드 정정 후, 아래 이력 참조)_
  - 증거: `{"node_count": 28, "edge_count": 27, "layers": {"1": 10, "2": 1, "3": 5, "4": 3, "5": 9}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[config_2] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 18, "edge_count": 17, "layers": {"1": 10, "2": 1, "3": 5, "4": 2, "5": 0}, "missing_in_api": [], "extra_in_api": []}`
- [**실패**] graph API[candidate_status] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers) — _재시험으로 대체: 같은 항목을 수정·재실행해 통과(시험 코드 정정 후, 아래 이력 참조)_
  - 증거: `{"node_count": 47, "edge_count": 44, "layers": {"1": 19, "2": 4, "3": 9, "4": 6, "5": 9}, "missing_in_api": [], "extra_in_api": []}`
- [통과] reverse trace: business step → rule version → decision → candidate → correction → model output → source span (UI-independent /path == Cypher chain)
  - 증거: `{"run_step": "step_8cf44754bbaa4438ac327e03334fb7c4", "chains": [{"step": "step_8cf44754bbaa4438ac327e03334fb7c4", "rv": "R-URGENCY-01@1", "d": "rdec_ae5e2330872a441ea3fb562b5c28eaf8", "c": "cand_861307de943efe054b1e407e", "cor": "cor_3ed68e6a980e4aacba33b94e29d7f632", "o": "mout_45caafb4e2f64ebdb7ddb99a4d50a2ca", "e": "esp_65cd3dfb4cac406091de5cd3017d295c"}, {"step": "step_8cf44754bbaa4438ac327e03334fb7c4", "rv": "R-URGENCY-01@1", "d": "rdec_ae5e2330872a441ea3fb562b5c28eaf8", "c": "cand_861307de943efe054b1e407e", "cor": "cor_b883b34442f34569bce57d37248bbd8f", "o": "mout_01db8264662541e59a2bc6edcfe70abc", "e": "esp_d2376c22cea44767a00d3e7b2b8b9ff7"}, {"step": "step_8cf44754bbaa4438ac327e0333…`
- [통과] forward trace: source span → model output → correction → candidate → decision → rule version → business step (rule applied to the new request)
  - 증거: `{"span": "esp_65cd3dfb4cac406091de5cd3017d295c", "downstream_count": 10, "reaches_step": "step_8cf44754bbaa4438ac327e03334fb7c4", "path": ["esp_65cd3dfb4cac406091de5cd3017d295c", "mout_45caafb4e2f64ebdb7ddb99a4d50a2ca", "cor_3ed68e6a980e4aacba33b94e29d7f632", "cand_861307de943efe054b1e407e", "rdec_ae5e2330872a441ea3fb562b5c28eaf8", "R-URGENCY-01@1", "step_8cf44754bbaa4438ac327e03334fb7c4"]}`
- [통과] node detail refs carry the same IDs as Flow/Learning (request_id, run_id, step_id, rule_id, rule_version, config_version)
  - 증거: `{"refs": {"run_id": "run_efb9b2f49eae496f9b334a0138fcd7d2", "request_id": "req_9163956b00194546bd0221bcbdd50ac9", "step_id": "step_8cf44754bbaa4438ac327e03334fb7c4"}, "source_link_null_without_can_read_source": true}`
- [통과] graph API[request] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 44, "edge_count": 42, "layers": {"1": 31, "2": 2, "3": 7, "4": 2, "5": 2}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[run] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 44, "edge_count": 42, "layers": {"1": 31, "2": 2, "3": 7, "4": 2, "5": 2}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[rule_urgency] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 16, "edge_count": 15, "layers": {"1": 9, "2": 1, "3": 2, "4": 3, "5": 1}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[rule_ai_need] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 28, "edge_count": 27, "layers": {"1": 10, "2": 1, "3": 5, "4": 3, "5": 9}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[config_2] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 18, "edge_count": 17, "layers": {"1": 10, "2": 1, "3": 5, "4": 2, "5": 0}, "missing_in_api": [], "extra_in_api": []}`
- [통과] graph API[candidate_status] nodes/edges == Neo4j stored nodes and ALL stored relationships among them (counts, layers)
  - 증거: `{"node_count": 47, "edge_count": 44, "layers": {"1": 19, "2": 4, "3": 9, "4": 6, "5": 9}, "missing_in_api": [], "extra_in_api": []}`
- [통과] reverse trace: business step → rule version → decision → candidate → correction → model output → source span (UI-independent /path == Cypher chain)
  - 증거: `{"run_step": "step_8cf44754bbaa4438ac327e03334fb7c4", "chains": [{"step": "step_8cf44754bbaa4438ac327e03334fb7c4", "rv": "R-URGENCY-01@1", "d": "rdec_ae5e2330872a441ea3fb562b5c28eaf8", "c": "cand_861307de943efe054b1e407e", "cor": "cor_3ed68e6a980e4aacba33b94e29d7f632", "o": "mout_45caafb4e2f64ebdb7ddb99a4d50a2ca", "e": "esp_65cd3dfb4cac406091de5cd3017d295c"}, {"step": "step_8cf44754bbaa4438ac327e03334fb7c4", "rv": "R-URGENCY-01@1", "d": "rdec_ae5e2330872a441ea3fb562b5c28eaf8", "c": "cand_861307de943efe054b1e407e", "cor": "cor_b883b34442f34569bce57d37248bbd8f", "o": "mout_01db8264662541e59a2bc6edcfe70abc", "e": "esp_d2376c22cea44767a00d3e7b2b8b9ff7"}, {"step": "step_8cf44754bbaa4438ac327e0333…`
- [통과] forward trace: source span → model output → correction → candidate → decision → rule version → business step (rule applied to the new request)
  - 증거: `{"span": "esp_65cd3dfb4cac406091de5cd3017d295c", "downstream_count": 10, "reaches_step": "step_8cf44754bbaa4438ac327e03334fb7c4", "path": ["esp_65cd3dfb4cac406091de5cd3017d295c", "mout_45caafb4e2f64ebdb7ddb99a4d50a2ca", "cor_3ed68e6a980e4aacba33b94e29d7f632", "cand_861307de943efe054b1e407e", "rdec_ae5e2330872a441ea3fb562b5c28eaf8", "R-URGENCY-01@1", "step_8cf44754bbaa4438ac327e03334fb7c4"]}`
- [통과] node detail refs carry the same IDs as Flow/Learning (request_id, run_id, step_id, rule_id, rule_version, config_version)
  - 증거: `{"refs": {"run_id": "run_efb9b2f49eae496f9b334a0138fcd7d2", "request_id": "req_9163956b00194546bd0221bcbdd50ac9", "step_id": "step_8cf44754bbaa4438ac327e03334fb7c4"}, "source_link_null_without_can_read_source": true}`
- [브라우저 ui1: **timedOut**] [X06] judgment map: nodes/edges = graph API = DB, bottom-up trace to source span, top-down trace, list view keyboard, Flow/Topology/Learning IDs — [31mTest timeout of 240000ms exceeded.[39m
- [브라우저 ui1: **failed**] [X06] judgment map: nodes/edges = graph API = DB, bottom-up trace to source span, top-down trace, list view keyboard, Flow/Topology/Learning IDs — Error: [2mexpect([22m[31mreceived[39m[2m).[22mtoEqual[2m([22m[32mexpected[39m[2m) // deep equality[22m
  - 화면 값: `[{"map_nodes": 44, "map_edges": 42, "flow_href": "/observatory?run_id=run_efb9b2f49eae496f9b334a0138fcd7d2", "learning_href": "/learning"}]`
- [브라우저 ui1: 통과] [X06] judgment map: nodes/edges = graph API = DB, bottom-up trace to source span, top-down trace, list view keyboard, Flow/Topology/Learning IDs
  - 화면 값: `[{"map_nodes": 44, "map_edges": 42, "flow_href": "/observatory?run_id=run_efb9b2f49eae496f9b334a0138fcd7d2", "learning_href": "/learning"}, {"rule_map": [16, 15]}]`
- [브라우저 ui1: 통과] [X06] judgment map: nodes/edges = graph API = DB, bottom-up trace to source span, top-down trace, list view keyboard, Flow/Topology/Learning IDs
  - 화면 값: `[{"map_nodes": 44, "map_edges": 42, "flow_href": "/observatory?run_id=run_efb9b2f49eae496f9b334a0138fcd7d2", "learning_href": "/learning"}, {"rule_map": [16, 15]}]`
- [브라우저 ui2: 통과] [X06] criteria filters (request / rule / Config version / status), zoom controls — counts follow the graph API
  - 화면 값: `[{"request_id": [44, 42], "rule_id": [22, 21], "config_version": [18, 17], "status_published": [51, 53]}]`

### X07 — 통과

- [**실패**] in-flight run started before the stop keeps the pinned (old) Config version and still applies the rule — _재시험으로 대체: stop landed while the run was still pending (not started); retested after the run pinned its Config_
  - 증거: `{"request": "req_1653c8a6a84a465f929389a2939b96ff", "run": "run_8a0fae6e13184ac1aa8b1785c3628310", "run_status_when_stop_called": {"id": "run_8a0fae6e13184ac1aa8b1785c3628310", "status": "pending", "cfg": null}, "run_config_version": 4, "stop_config_version": 4, "applied": [{"rule": "R-URGENCY-01@1", "outcome": "out_of_scope"}], "judgment_committed": "2026-10-03T09:53:08.629Z", "ai_need": "불필요"}`
- [통과] after stop: active rules lack the rule; new request has no APPLIED for it and keeps the model value (불필요)
  - 증거: `{"request": "req_160dcd95728641b7ba2c41c7a01fb254", "run": "run_e6ab1d7c5ef74f0ca19c5c0ff90700a3", "active_config": 4, "active_rules": ["R-URGENCY-01@1"], "applied": [{"rule": "R-URGENCY-01@1", "outcome": "out_of_scope"}], "ai_need": "불필요"}`
- [통과] publish v2 then revert to v1 = new Config versions each; v2 used before, v1 used after (APPLIED rule_version), Config pinned per run
  - 증거: `{"stop_cfg": 4, "v2_cfg": 5, "revert_cfg": 6, "v2_request": {"req": "req_5d24648202a04d01b7c96729503c9de2", "applied": [{"rule": "R-URGENCY-01@1", "outcome": "out_of_scope"}, {"rule": "R-AI_NEED-01@2", "outcome": "used"}]}, "revert_request": {"req": "req_93a9da07d6ec433ea912c76e2f2333f4", "applied": [{"rule": "R-AI_NEED-01@1", "outcome": "used"}, {"rule": "R-URGENCY-01@1", "outcome": "out_of_scope"}]}, "rule_version_status": [{"v": 1, "s": "published"}, {"v": 2, "s": "reverted"}], "active_rules": ["R-URGENCY-01@1", "R-AI_NEED-01@1"]}`
- [통과] past records unchanged: earlier APPLIED rows (before/after/outcome), earlier Judgments (hash), earlier Config versions identical
  - 증거: `{"applied_rows_before": 10, "applied_rows_now": 10, "judgments_checked": 9, "config_versions_checked": 3}`
- [통과] (retest) run in flight when the stop was published keeps the pinned old Config version and applies the rule; the stop is a new Config version
  - 증거: `{"attempt": 1, "request": "req_0f3fe5e24d764600bc87e8a2dcc91787", "run": "run_ff8f379c293c41f795d95b0c3995c994", "state_when_stop_called": {"id": "run_ff8f379c293c41f795d95b0c3995c994", "status": "running", "cfg": 6, "committed": false}, "active_config_before_stop": 6, "stop_config": 7, "run_config_version": 6, "judgment_committed_at": "2026-10-03T09:53:43.517Z", "applied": [{"rule": "R-AI_NEED-01@1", "outcome": "used", "before": "\"불필요\"", "after": "\"필요\""}, {"rule": "R-URGENCY-01@1", "outcome": "out_of_scope", "before": "\"판단 보류\"", "after": "\"판단 보류\""}], "ai_need": "필요"}`
- [브라우저 ui2: **failed**] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload) — Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoContainText[2m([22m[32mexpected[39m[2m)[22m failed
- [브라우저 ui2: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 8, "v1": {"applications": 11, "configs": [2, 6, 8]}, "v2": {"applications": 1, "configs": [5]}, "configs": {"revert": 6, "stop": 4, "v2": 5}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 18시 37분 45초 · code:candidate@v1"}]`
- [브라우저 ui3: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 8, "v1": {"applications": 11, "configs": [2, 6, 8]}, "v2": {"applications": 1, "configs": [5]}, "configs": {"revert": 6, "stop": 4, "v2": 5}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 18시 37분 45초 · code:candidate@v1"}]`

### X08 — 통과

- [통과] API server + worker + collector restarted: DB truth and public API snapshot before/after differ in 0 fields (candidates, decisions, rule versions, relations, APPLIED rows, validation cards, configs, graph, effects)
  - 증거: `{"differences": [], "difference_count": 0, "compared": {"db": {"applied": 18, "candidates": 5, "configs": 8, "corrections": 8, "rule_versions": 4, "validations": 6}, "api_candidates": 5, "api_rules": 3, "graph_criteria": 6, "graph_nodes": {"candidate_status": 66, "config_2": 18, "request": 44, "rule_ai_need": 32, "rule_urgency": 21, "run": 44}, "graph_edges": {"candidate_status": 72, "config_2": 17, "request": 42, "rule_ai_need": 31, "rule_urgency": 20, "run": 42}, "judgments": 9}, "pre_sha": "f4a2266b6b7ee096", "post_sha": "f4a2266b6b7ee096"}`
- [통과] after restart the new worker processes a new request under the active Config and applies the restored rule (APPLIED recorded)
  - 증거: `{"request": "req_bd8a4c33748849238d8e6029b8ced18a", "run": "run_9878dea304e34c49b40f29298505d4b6", "active_config": 8, "applied": [{"rule": "R-AI_NEED-01@1", "outcome": "used", "before": "\"불필요\"", "after": "\"필요\""}, {"rule": "R-URGENCY-01@1", "outcome": "out_of_scope", "before": "\"판단 보류\"", "after": "\"판단 보류\""}], "ai_need": "필요"}`
- [브라우저 ui2: **failed**] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload) — Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoContainText[2m([22m[32mexpected[39m[2m)[22m failed
- [브라우저 ui2: 통과] [X08] judgment map and trace: counts and IDs equal the stored snapshot after reload
  - 화면 값: `[{"checked": {"candidate_status": [66, 72], "config_2": [18, 17], "request": [44, 42], "rule_ai_need": [32, 31], "rule_urgency": [21, 20], "run": [44, 42]}}]`
- [브라우저 ui2: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 8, "v1": {"applications": 11, "configs": [2, 6, 8]}, "v2": {"applications": 1, "configs": [5]}, "configs": {"revert": 6, "stop": 4, "v2": 5}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 18시 37분 45초 · code:candidate@v1"}]`
- [브라우저 ui2: 통과] [X08] judgment map and trace: counts and IDs equal the stored snapshot after reload
  - 화면 값: `[{"checked": {"candidate_status": [66, 72], "config_2": [18, 17], "request": [44, 42], "rule_ai_need": [32, 31], "rule_urgency": [21, 20], "run": [44, 42]}}]`
- [브라우저 ui3: 통과] [X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)
  - 화면 값: `[{"changed_config_versions": 8, "v1": {"applications": 11, "configs": [2, 6, 8]}, "v2": {"applications": 1, "configs": [5]}, "configs": {"revert": 6, "stop": 4, "v2": 5}, "timeline": "후보 제안\nAI 가설\n2026. 10. 3. 18시 37분 45초 · code:candidate@v1"}]`
- [브라우저 ui3: 통과] [X08] judgment map and trace: counts and IDs equal the stored snapshot after reload
  - 화면 값: `[{"checked": {"candidate_status": [66, 72], "config_2": [18, 17], "request": [44, 42], "rule_ai_need": [32, 31], "rule_urgency": [21, 20], "run": [44, 42]}}]`

### X09 — 통과 (표본 부족 경로만 시험)

- [통과] effects API counts (before/after/used/out_of_scope: sample, change, correction, review, failure) == independent DB computation
  - 증거: `{"api": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0, "latency_sample_count": 8, "latency_p50_ms": 2924.5, "latency_p95_ms": 4074.35}, "after": {"sample_count": 4, "corrections": 0, "review_transitions": 4, "failures": 0, "classification_changes": 3, "latency_sample_count": 4, "latency_p50_ms": 2705.0, "latency_p95_ms": 2797.8}, "used": {"sample_count": 3, "corrections": 0, "review_transitions": 3, "failures": 0, "classification_changes": 3, "latency_sample_count": 3, "latency_p50_ms": 2670.0, "latency_p95_ms": 2733.0}, "out_of_scope": {"sample_count": 1, "corrections": 0, "review_transitions": 1, "failures": 0, "classif…`
- [통과] sample below minimum -> effect 'insufficient_sample' (undetermined), shadow runs excluded, SLO not included
  - 증거: `{"effect": "insufficient_sample", "minimum_sample": 20, "samples": 12, "shadow_runs_excluded": 1, "slo_included": false}`
- [브라우저 ui1: 통과] [X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족
  - 화면 값: `[{"ui_used": 3, "ui_out": 6, "db": {"before": {"sample_count": 8, "corrections": 5, "review_transitions": 8, "failures": 0, "classification_changes": 0}, "after": {"sample_count": 9, "corrections": 3, "review_transitions": 9, "failures": 0, "classification_changes": 3}, "used": {"sample_count": 3, "corrections": 0, "review_transitions": 3, "failures": 0, "classification_changes": 3}, "out_of_scope": {"sample_count": 6, "corrections": 3, "review_transitions": 6, "failures": 0, "classification_cha…`

## 4. X10 회귀

X10은 **기존 승인·권한·중복 배정 방지·재생 무부작용·SLO 집계**가 확장 이후에도 유지되는지 재실행한 결과다. 기존 게이트(G01–G12)의 판정은 T27 소관이며 여기서는 시험 재실행 결과만 기록한다(섞어 판정하지 않음).

| 실행 | 명령 | 결과 |
| --- | --- | --- |
| 백엔드 전체(저장소 `make test`의 백엔드 부분과 동일: `cd backend && .venv/bin/pytest`, 추가 환경변수 없음) | `pytest -q` | **129 통과, 1 건너뜀**, 100.25초 (1차 실행 128 통과·1 건너뜀 87초, 2차 128/1 88초 — 이후 회귀 시험 1건 추가). 건너뜀 1건: `tests/live/test_judgment_live.py` ('JEV_MODE=live와 live 자격 필요' 조건 시험, T38과 무관) |
| 프런트 `make test` 프런트 부분 | `cd frontend && npm run test` | vitest 11 파일 **34 통과** (Learning 8, JudgmentMap 6, Monitoring 3, Policy 2, Review 1 포함) |
| 타입 검사 | `npm run typecheck` | 오류 없음 |
| 기본 수집 분리 | `pytest --collect-only -q \| grep -c acceptance` | 0 (tests/acceptance/extension은 `X38_RUN=1`일 때만 수집) |

기존 게이트 관련 시험 재실행(모두 통과, 위 전체 실행에 포함, 별도 재실행 60건 통과):

| 기존 게이트 | 시험 | 결과 |
| --- | --- | --- |
| G04 검토(승인·수정·반려·정보 요청, 승인 전 배정 불가) | `test_review_assignment.py` 13건(4결정·감사 이력·권한/tenant/CSRF·자동 경로 재검증) | 통과 |
| G05 업무(중복 배정 없음) | `test_review_assignment.py::test_concurrent_approvals_one_assignment_and_idempotency`(동시 승인 20개 → 배정 1개), `test_reanalysis_boundary.py` 3건 | 통과 |
| G06 정책·그래프 | `test_policy_versions.py` 6건, `test_judgment_graph.py` 5건, `test_rules_integration.py` 7건(게시·적용·중단·되돌리기·재시작) | 통과 |
| G07 흐름·재생 | `test_observe_api.py`, 프런트 `playback.test.ts`, **실측**: 저장된 실행의 playback/flow/topology 호출 전후 13개 라벨 노드 수·속성 해시 동일 | 통과 |
| G08 SSE | `test_sse_events.py`(전체 실행에 포함) | 통과 |
| G09 관찰 | `test_monitoring_collector.py` 13건, 프런트 `Monitoring.test.tsx` 3건, 실측: 섀도 검증 전후 SLO 분모·알림 동일(X04 재시험) | 통과 |
| G11 안전 | `test_auth.py` 3건, `test_ingest_api.py`(CSRF·역할·tenant·원문 게이트), 권한 403 실측(X03) | 통과 |

참고: 저장소 전체 `ruff check jevtriage tests`는 이 작업 시작 이후에도 다른 작업자 파일 포함 다수의 기존 경고(실행 시점 51~63건)가 있다. 이 작업의 확장 시험 디렉터리는 대부분 정리했다(남은 1건). 게이트 판정 대상이 아니다. 전체 E2E(`learning.spec.ts`·`judgment-map.spec.ts`)는 규칙을 게시하므로 이 작업의 전용 tenant 상태를 바꿀 수 있어 재실행하지 않았다(패턴만 재사용).

## 5. 발견 사항

### 발견 결함과 조치

| # | 구분 | 내용 | 조치 |
| --- | --- | --- | --- |
| F1 | **결함(수정함)** | `POST /api/learning/candidates`(사람이 후보 제안)가 **항상 500**: `candidates_api.py`의 `any(not await … for …)`는 async 제너레이터라 `TypeError`. (T36 화면에는 사람 제안 UI가 없어 가려져 있었음) | `jevtriage/learning/candidates_api.py` 반복문으로 최소 수정 + 회귀 시험 `tests/integration/test_candidates_human_proposal.py` 추가(원본 코드에서 실패, 수정 후 통과 확인) |
| F2 | **결함(수정함)** | 후보가 제안하는 `rule_id`가 `R-AI-NEED-01`(필드의 `_`를 `-`로 치환)인데 서버 규칙 ID 형식 `^R-[A-Z_]+-[0-9]{2,}$`가 `-`를 허용하지 않아 그대로 쓰면 `RULE_ID_INVALID`. 화면은 자체 기본값(`R-AI_NEED-01`)을 써서 가려졌다 | `candidates.py`·`candidates_api.py`에서 치환 제거(`R-AI_NEED-01`). 같은 파일의 import 정렬(ruff I001)도 함께 정리 |
| F3 | **제한(보고)** | Trace '규칙 적용' 단계는 존재하고 실행 ID·Config 버전·최종 판단 값을 보이지만, **단계 상세(`/api/observe/steps/{id}`·Flow 서랍)는 RuleApplication(규칙 버전·outcome·전후 값)을 보여 주지 않는다**(`output_summary={}`). 규칙 버전·전후 값은 Judgment API `rule_effects`와 판단 맵 `APPLIED` 연결에서 확인된다 | 수정하지 않음(T17 영역). X05는 '실행 기록(APPLIED)=판단 API=Trace 단계 ID·Config·판단 값' 대조로 판정 |
| F4 | 관찰 | 불변 조건 검사가 리터럴(`feasibility=가능`, `urgency=일반`, 검토 경로 제거)만 거절한다. 이 시나리오에서 `urgency 긴급→판단 보류` 규칙(`R-URGENCY-01@1`)이 거절 없이 승인·게시되어 실제로 긴급도를 낮췄다. 명세의 '완화 거절'보다 좁다 | 수정하지 않음(정책 결정 필요) — 코디네이터 판단 요청 |
| F5 | 관찰 | 서버는 `자료 부족` 후보의 승인·규칙 버전 생성·검증을 막지 않는다(`cand_e123…`를 승인해 검증까지 수행함). 화면은 효과 주장을 하지 않는 문구만 표시 | 수정하지 않음 |
| F6 | 관찰 | 섀도 검증은 `Run`과 `ValidationRun`을 같은 `id`로 저장한다(`val_…`). id만으로 노드를 찾는 질의가 두 라벨에 걸린다 | 수정하지 않음(그래프 API는 라벨로 구분해 영향 없음) |
| F7 | 관찰 | Flow API(`/api/observe/runs/{id}/flow`) 노드의 `started_at/ended_at`이 Neo4j DateTime 내부 구조 그대로(`_DateTime__date…`) 직렬화됨 | 수정하지 않음(T17 영역) |
| F8 | 환경 사건(제품 결함 아님) | 09:35Z 무렵 다른 작업자(T26 백업 스크립트)가 공유 Neo4j 컨테이너를 잠시 정지해 처음 띄운 worker가 종료됨(코디네이터 통지로 확인). 정상화 확인 후 이 작업의 worker만 다시 띄우고 컨테이너는 건드리지 않음. 해당 시간대에 실패한 단계는 없었고 데이터(tenant)는 유지됨 | 사건으로만 보고 |
| F9 | 정정 | `ruff --fix`를 `tests/acceptance` 전체에 실행해 **다른 작업자의 `tests/acceptance/*.py`가 자동 수정되었을 수 있다**(import 정렬·미사용 import 수준, 변경 내용 미추적). 이후 이 작업 파일에만 실행 | 코디네이터 확인 요청 |

### 시험 설계상 정정(숨기지 않음)

- X03 `policy_editor … rules diff` 첫 시도는 유효하지 않은 규칙 ID(F2)로 `SCHEMA_INVALID`가 되어 `RULE_ADMIN_REQUIRED` 경로에 도달하지 못함 → 유효 ID로 재시험 통과.
- X04 `monitoring … unchanged` 첫 시도는 수집기 미기동·창 시각 변동으로 무의미(실패 기록) → 수집기를 켠 재시험 2회(첫 재시험은 `summary.kinds.shadow_validation`이 +1, 이는 분모가 아니라 섀도 별도 집계 → 제외 후 통과, 차이는 증거에 보존).
- X05 '약화 규칙 거절' 첫 PASS는 후보 생성 단계(404→500, F1)에서 끝나 무효 → 수정 후 재시험 통과(승인까지 한 뒤 규칙 버전 생성에서 `RULE_INVALID` 422).
- X06 그래프 대조 3건 첫 실패는 시험 오류(섀도 `Run`/`ValidationRun` id 공유, F6) → 라벨 기준 매칭으로 정정.
- X07 진행 중 실행 첫 시도는 Run이 `pending`(아직 Config 미고정)일 때 중단이 들어가 무효 → Config 고정 후 중단을 넣는 재시험 통과.

### 남은 제한

- 모든 분류는 실제 Jev(`mode=live`)이지만 같은 문장 템플릿이라 판단이 거의 동일(`불필요/IT팀/정보 부족/판단 보류`)하다. 다양한 입력에서의 규칙 효과는 이 작업의 범위가 아니다.
- X09: 표본 충분 시 `개선 확인` 등 판정 경로는 이 시나리오(전 8건·후 몇 건 < 최소 20)에서 발생하지 않아 T35 통합 시험(40건 알려진 표본)에 의존한다.
- 담당 조직(lead_org) 수정 방향은 시험하지 않고 분류(ai_need) 방향만 사용했다(명세의 '또는').
- 근거 원문 연결(EvidenceSpan)은 실제 Jev가 인용한 긴급도 출력(의료 문장)으로만 확보되어 2번째 규칙(긴급도)으로 끝까지 역추적했고, 1번째 규칙(회의실 문장)의 수정 기록은 인용이 없어 `evidence_span_ids=[]`다.
- 선행 작업 T21·T22는 TASK.md상 '대기'였다. T38의 선행 확장 작업(T36·T37)은 완료 상태에서 수행했다.


## 6. 재현 방법

```sh
make up
cd backend
.venv/bin/python tests/acceptance/extension/provision_tenant.py <tenant>
WORKER: .venv/bin/python -m jevtriage.jobs.worker --tenant <tenant>   # API: uvicorn jevtriage.main:app --port <port>
export X38_OUT=<artifacts/validation/<ts>/extension> X38_TENANT=<tenant> X38_API=http://127.0.0.1:<port>
.venv/bin/python -m tests.acceptance.extension.scenario seed corrections rules apply weaken notes effects chain2 graph lifecycle inflight shadow_monitoring
X38_SUFFIX=ui1 .venv/bin/python -m tests.acceptance.extension.scenario export   # then: cd ../frontend && X38_PHASE=ui1 npx playwright test -c playwright.extension.config.ts
... snapshot (pre) → 프로세스 재시작 → snapshot (post) → diff → ui3 ...
.venv/bin/python -m tests.acceptance.extension.report
```
