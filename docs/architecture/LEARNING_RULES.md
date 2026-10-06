# 규칙 수명·실행 적용 (T32/T34)

규칙 후보는 `RuleCandidate.proposed_body`에 `rule-v1` JSON을 보관한다. 규칙 관리자의 결정은 `RuleDecision-[:DECIDES]->RuleCandidate`로 남으며, 승인된 결정만 `RuleVersion-[:DERIVED_FROM]->RuleDecision`을 만들 수 있다. 범위를 바꿔 승인하면 결정의 `confirmed_scope`를 최종 본문에 넣는다. 버전은 `validating`으로 시작하고, 연결된 `ValidationRun`이 `completed`이며 `side_effects=0`일 때 `validated`로 전이한다. 게시 전 검증 완료 상태를 서버가 다시 확인한다.

API 쓰기는 `rule_admin` 세션·CSRF·`Idempotency-Key`·사유가 필요하다. 게시·중단·되돌리기는 활성 Config 버전 기대값을 검사한 단일 Neo4j 쓰기 트랜잭션에서 새 `ConfigVersion`, 감사 기록, `rule.*` 이벤트를 함께 만든다. 일반 `policy_editor` 경로는 `rules` 차이를 게시할 수 없다. 규칙 게시의 `rules` 항목에는 본문 식별자·효과·대상·범위·동작·검증된 컨텍스트 문장을 저장한다. 저장·게시·되돌리기마다 정책 스키마와 안전 불변 조건을 검사한다.

실행 핸들러는 Run 시작 시점의 Config 버전을 고정하고 그 버전의 규칙 목록만 사용한다. Decision AI 호출 이전에 컨텍스트 규칙의 `context_text`를 질문 state의 `operating_guidance` 데이터로 전달한다. Decision AI 판단 후 `규칙 적용` RunStep에서 순수 함수 `apply_rules`를 호출하고, 기존 eligibility 서버 조건을 다시 평가한다. 결과 저장과 같은 `ctx.commit(affects_request=True)` 안에서 `(RunStep)-[:APPLIED {outcome,before,after,rule_version}]->(RuleVersion)` 및 Judgment의 `rule_effects`를 기록한다. API는 규칙 버전·효과·사용/범위 밖/충돌·전후 값·Config 버전을 원문 없이 노출한다.

결정적 술어만 허용한다: 분류 필드의 `eq`/`in`, Noul 신호의 `gte`/`lte`, 카탈로그 업무 존재, 요청 조직. 동작은 target별 허용 목록으로 제한한다. `urgency`는 `긴급` 지정 또는 검토 사유 추가, `feasibility`는 `조건부 가능`·`현재 불가`·`정보 부족` 지정, `ai_need`는 정의된 네 분류값 지정, `lead_org`는 `AI팀`·`IT팀`·`현업` 지정, `collab_orgs`는 이 조직 중 하나 추가, `review_route`는 검토 사유 추가만 허용한다. 위험 필드나 필수 검토 표시를 바꾸는 동작은 허용하지 않는다. 위반은 저장·버전 생성·게시·되돌리기에서 HTTP 422 `RULE_INVARIANT`로 거절한다. 과거 Config에 이미 남은 위반 규칙은 적용 시 `blocked_by_invariant`로 기록하고 판단을 바꾸지 않는다. 같은 target에서 뒤에 게시된 규칙이 우선하며 필수 검토 추가가 그보다 우선한다. 모든 활성 규칙의 범위 밖 결과도 기록한다. 과거 Judgment와 APPLIED 관계는 새 Config 게시로 변경하지 않는다.

검증: `make up` 다음 `cd backend && .venv/bin/pytest tests/integration/test_rules_integration.py -q`에서 실제 Neo4j와 mock Decision AI로 권한·상태 전이·안전 검사·게시·적용·범위 밖·버전 고정·중단·되돌리기·드라이버 재생성을 확인한다. mock 결과는 분류 품질 승인 증거가 아니다.

## 규칙 조회와 변경 권한 (FIX-LEARN)

규칙 목록·상세·효과는 `rule:read` 권한을 사용하며 reviewer·operator·rule_admin이 조회한다. tenant 경계는 저장소 조회에서 강제한다. reviewer에게는 각 버전의 `scope.all[].requester_org`와 소속 조직이 겹치는 버전만 노출하며 조직 조건 없는 규칙은 tenant 공통으로 읽을 수 있다. operator와 rule_admin은 tenant 전체 범위다. 가려진 버전은 목록의 최신 버전·버전 수에서도 제외하며 범위 밖 상세·효과는 404다. 원문 필드는 기존 `can_read_source` 권한대로 제거한다. 효과 실행 집계도 reviewer의 요청 범위로 제한한다.

후보 결정·버전 생성·검증·게시·중단·되돌리기는 기존 rule_admin 전용 권한을 유지한다. 규칙 학습 화면은 조회 역할에도 규칙 버전과 게시 후 관찰을 연결하고 변경 버튼은 비활성으로 표시한다.


## 원문 키워드 조건 (RULE_KEYWORD)

`{"text":{"contains_any":["서버","VPN"]}}`은 해당 revision의 모든 마스킹 전 EvidenceSpan에서 하나라도 포함되면 참이다. 문자마다 NFKC·casefold 후 공백·제어·서식 문자를 제거하며, 키워드 1~20개·정규화 후 1~50자·정규화 중복 금지를 검사한다. 조건들은 기존처럼 AND이며 text 조건을 여러 개 두면 모두 포함을 표현한다. 원문 단위가 없는 실행에서는 거짓으로 처리하고, 키워드 섀도 표본의 원문을 읽을 수 없으면 `input_unavailable`로 실패를 남긴다. `context` 조건에는 요청 조직과 원문 키워드만 허용한다. 일치 기록은 규칙당 최대 5개의 `{unit_id,char_start,char_end,keyword}`이며 원문 조각을 포함하지 않는다. `rule_effects`에는 `target`과 `rule:<id>@v<version>` 출처가, `APPLIED`에는 `source`가 저장된다. 결과·검토 화면은 규칙 근거와 모델 원판단 근거를 구분하고 기존 원문 권한을 유지한다. API와 worker를 함께 배포한 뒤 키워드 규칙을 게시한다. 상세 계약과 검증 기록은 [RULE_KEYWORD.md](RULE_KEYWORD.md)를 따른다.
