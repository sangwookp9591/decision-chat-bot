# 원문 키워드 규칙과 규칙 출처 표시 (ADR)

- 상태: 구현 및 수용 검증 완료
- 날짜: 2026-10-06
- 관련: [LEARNING_RULES.md](LEARNING_RULES.md), [LEARNING_VALIDATION.md](LEARNING_VALIDATION.md), [POLICY.md](POLICY.md), [LLM_ASSIST.md](LLM_ASSIST.md)

## 1. 배경

규칙(`domain/rules.py`, `rule-v1`)의 조건은 모두 AND로 묶이고, 지금 쓸 수 있는 조건은 네 가지뿐이다.

- 모델 분류값(`field`)
- 모델 신호(`signal`)
- 카탈로그 업무 유형(`catalog_task`)
- 요청자 조직(`requester_org`)

그래서 "서버·VPN 요청은 무조건 IT팀" 같은 운영 규칙을 쓸 수 없다.

규칙 적용 기록은 다음 두 곳에 저장되지만 화면에는 나오지 않는다.

- `Judgment.rule_effects`
- `APPLIED` 관계(`judgment/service.py` 235-251)

또 근거는 규칙을 적용하기 전 모델 값을 기준으로 연결된다. 규칙이 `lead_org`를 바꾸면 화면의 근거가 바뀐 값과 어긋난다.

관리자가 규칙을 직접 등록하는 화면(`Proposal.tsx`)은 조건을 JSON으로 받는다. 예시 `{"requester_org":"IT팀"}`은 실제 비교값과 맞지 않는다. 비교 대상인 `Request.org_ids`는 `t-alpha-it` 같은 조직 ID다(`review/service.py` `org_key`: `{tenant}-ai|it|business`).

## 2. 결정 요약

| # | 결정 | 버린 대안 |
|---|---|---|
| K1 | 조건 `{"text":{"contains_any":[…]}}` 하나만 더한다. 정규식은 받지 않는다. "모두 포함"은 text 조건 여러 개를 AND로 묶어 표현한다 | 정규식, `contains_all`, 단어 경계 옵션 |
| K2 | 정규화는 문자마다 NFKC → casefold → 공백·서식 문자 제거다. 한국어 띄어쓰기 차이("서버 점검"과 "서버점검")를 흡수하기 위해서다 | 공백을 하나로 접기만 하는 방식 |
| K3 | **마스킹 전 원문**의 EvidenceSpan 단위로 판정한다. 판정은 서버 안에서 결정적으로 하고, 결과는 밖으로 보내지 않는다 | 마스킹 후 텍스트로 판정 |
| K4 | 적용 시점은 그대로 둔다(판단 뒤 보정). text 조건은 모델 없이 판정할 수 있으므로 **context 규칙에도 허용한다** | rule 효과만 허용 |
| K5 | 규칙이 바꾼 값마다 출처 `rule:<id>@v<ver>`와 일치 범위(`unit_id`, 단위 안 offset, keyword)를 `rule_effects`에 기록한다. 화면은 이것으로 "규칙 적용"과 규칙 근거를 보여 주고, 모델 근거에는 "모델 원판단(<값>) 근거"라고 표시한다 | 그래프에 `RULE_CITES` 관계를 새로 만드는 안 |
| K6 | 등록 화면은 폼으로 바꾼다(키워드 칩, 실제 조직 목록에서 고르는 요청 조직, 판단 값). 나머지 조건은 "고급: 조건 JSON"에 남긴다. 서버는 조직 ID가 tenant에 있는지 확인한다 | 모든 조건을 폼으로 만드는 안 |

## 3. 조건 문법

```json
{"schema": "rule-v1", "rule_id": "R-LEAD_ORG-03", "version": 1, "effect": "rule", "target": "lead_org",
 "scope": {"all": [{"text": {"contains_any": ["서버", "VPN"]}}]},
 "action": {"set": "IT팀"}}
```

- `text` 조건 하나는 키워드 가운데 **하나라도** 원문에 있으면 참이다.
- `scope.all`의 조건들은 기존처럼 AND로 묶인다. 예를 들어 `[{"text":{"contains_any":["VPN"]}}, {"requester_org":"t-alpha-business"}]`는 "현업 조직이 VPN을 언급한 요청"이다.
- "무조건 IT팀"은 담당 조직 **분류값**을 정한다는 뜻이다. 자동 배정은 지금처럼 정책 조건(신뢰도, 근거, 위험)을 따른다. 규칙이 사람 검토를 건너뛰게 하지는 않는다. `Review.required_reviewer_org`는 규칙을 적용한 뒤의 `lead_org`를 쓴다(기존 동작).

## 4. 검증 규칙 (`validate_rule`)

`domain/rules.py`의 `scope.all` 반복문에 갈래 하나를 더한다.

| 검사 | 위반 시 |
|---|---|
| 조건의 키가 정확히 `{"text"}`이고, 값이 정확히 `{"contains_any"}`인 dict다 | `ValueError("invalid text predicate")` → `RULE_INVALID` 422 |
| `contains_any`는 길이 1~20인 list다 | 같음 |
| 각 원소는 `str`이고, 정규화 후 길이가 1~50자다 | 같음 |
| 정규화 후 중복이 없다 | `ValueError("duplicate keyword")` |

- 키워드는 저장할 때 **원래 표기를 그대로 둔다**(화면 표시용). 정규화는 판정할 때 한다.
- context 규칙의 검사는 이렇게 바꾼다. 지금은 모든 조건이 `requester_org`여야 하지만, 앞으로는 모든 조건이 `requester_org` 또는 `text`여야 한다. 둘 다 모델 호출 전에 판정할 수 있는 조건이다. 오류 문구는 그대로 둔다.
- `learning/candidates_api.py` `propose`의 조건 키 허용 목록(108행)에 `"text"`를 더한다.

## 5. 정규화와 판정

```python
# domain/rules.py
_DROP = {"Zs", "Cc", "Cf"}          # 공백·제어·서식(zero-width 등) 문자

def normalize_for_match(text: str) -> tuple[str, list[int]]:
    """정규화 문자열과, 정규화 문자마다 원문에서의 위치를 함께 돌려준다."""
    out, index = [], []
    for i, ch in enumerate(text):
        for n in unicodedata.normalize("NFKC", ch).casefold():
            if n.isspace() or unicodedata.category(n) in _DROP:
                continue
            out.append(n)
            index.append(i)
    return "".join(out), index

def text_matches(clause: dict, units: list[dict], limit: int = 5) -> list[dict]:
    """[{unit_id, char_start, char_end, keyword}] 형태로 돌려준다.

    offset은 단위 원문 기준의 [start, end)다. 단위 순서와 키워드 순서대로 찾고 최대 limit건에서 멈춘다.
    """
```

- 예: "ＶＰＮ 접속"(전각), "vpn접속", "V P N"은 모두 키워드 `VPN`과 일치한다.
- 원문 범위는 `start = index[pos]`, `end = index[pos + len(kw) - 1] + 1`로 되돌린다.
- **알려진 한계.** 문자 단위로 NFKC를 적용하므로 분해형(NFD) 한글 자모로 저장된 원문은 완성형 키워드와 맞지 않는다. 입력 경로에서 본문은 대부분 NFC다. 실제로 문제가 되면 수집 단계(`ingest`)에서 EvidenceSpan을 NFC로 저장하도록 고친다. 코드에 `ponytail:` 주석으로 남긴다.

**판정 입력.** `features["text_units"] = [{"unit_id", "text"}]`. 이것은 `load_input`이 돌려주는 해당 revision의 **모든** EvidenceSpan이다. 채팅도 EvidenceSpan으로 저장되어 있다.

- 모델에 보내는 `select_units`의 12개·2,000자 제한은 적용하지 않는다. 판정 비용이 문자열 검색뿐이기 때문이다.
- `text_units`가 없으면 text 조건은 **거짓**이다. 과거 경로에서 규칙이 몰래 적용되는 일을 막기 위해서다.

**왜 마스킹 전 원문인가 (K3)**

- 판정은 서버 안에서 하므로 원문이 외부로 나가지 않는다.
- 마스킹 토큰(`[MASKED_IP_1]`)으로 바뀐 IP·계정 형태의 키워드도 맞출 수 있다.
- 화면 근거와 같은 원문 offset을 쓸 수 있다.

**공개되는 범위.** 일치 기록에는 위치(`unit_id`, offset)와 규칙의 키워드만 남기고 원문 조각은 남기지 않는다. 원문을 볼 수 있는지는 지금처럼 `can_read_source`와 `redact_source`가 정한다.

## 6. 판정 위치

| 효과 | 시점 | 코드 |
|---|---|---|
| `rule` | 지금처럼 모델 판단 뒤 "규칙 적용" 단계 | `apply_rules(result, rules, features={"signals", "requester_orgs", "text_units"})` |
| `context` | 지금처럼 모델 호출 전, 안내문(guidance) 선택 | 새 순수 함수 `context_rules_for(rules, features) -> list[str]`(context_text 목록) |

- `judgment/service.py` 82-87행의 안내문 선택 반복문을 `context_rules_for`로 바꾼다. `apply_rules`에 넘기는 `features`에는 `"text_units": units`를 더한다.
- 섀도 검증(`learning/shadow.py`)
  - 141행의 `all(c.get("requester_org") in orgs …)`를 `context_rules_for`로 바꾼다.
  - 후보 규칙이나 기준 규칙 가운데 하나라도 text 조건이 있으면 표본마다 `load_input(tenant, request_id, revision_id)`로 단위를 읽어 `features["text_units"]`에 넣는다. 지금 context 규칙에서 쓰는 호출과 같은 함수다.
  - 단위를 읽지 못한 표본은 기존 `failures`에 `reason:"input_unavailable"`로 기록한다. 이렇게 해야 키워드 규칙의 섀도 결과가 "변화 0건"으로 잘못 나오지 않는다.

## 7. 근거 연결 데이터 형태 (K5)

`apply_rules`가 만드는 application에 필드 세 개를 더한다: `target`, `source`, `matches`. 나머지는 기존 그대로다.

```json
{"rule_version": "R-LEAD_ORG-03@1",
 "source": "rule:R-LEAD_ORG-03@v1",
 "effect": "rule", "target": "lead_org",
 "outcome": "used", "before": "AI팀", "after": "IT팀",
 "config_version": 12,
 "matches": [{"unit_id": "esp_7f…", "char_start": 14, "char_end": 17, "keyword": "VPN"}]}
```

- `matches`는 **scope가 참일 때만** 채운다. text 조건이 없으면 `[]`다. 같은 규칙에서 최대 5건이다.
- `keyword`는 규칙에 적힌 원래 표기다.
- 저장은 지금처럼 `Judgment.rule_effects`(JSON)와 `APPLIED` 관계에 한다. `APPLIED`에는 `a.source`만 더한다.
- 일치 범위를 그래프 관계로 만들지는 않는다. 판단 맵이 규칙 근거를 그려야 할 때 `(:RunStep)-[:RULE_CITES {rule_version,char_start,char_end,keyword}]->(:EvidenceSpan)`을 더한다.

**바뀐 값과 근거를 맞추는 규칙.** 이 규칙은 화면 쪽 helper `ruleOverrides(rule_effects)`에서 계산한다.

- **대상.** `effect=="rule"`, `outcome=="used"`, `target`이 분류 키(`ai_need`·`feasibility`·`urgency`·`lead_org`)이고 `before != after`인 항목을 고른다. 그 결과로 `{target: {source, before, after, matches}}`를 만든다.
- **표시.** 그 분류는 "규칙 적용"으로 표시하고, 규칙 근거(matches)를 먼저 보여 준다.
- **모델 근거.** 모델 근거(ModelOutput CITES)는 지우지 않는다. 대신 "모델 원판단(`before`) 근거"라고 고쳐 표시한다. 저장된 사실은 바꾸지 않고 해석만 바로잡는다.
- `require_review`와 `add`(collab_orgs)는 분류를 바꾸지 않는다. 이것들은 "적용된 규칙" 목록에만 나온다.

## 8. API 변경

| 경로 | 변경 | 소유 |
|---|---|---|
| `GET /api/requests/{id}/judgment` | 없음. `rule_effects`를 이미 decode해서 돌려준다. 새 필드는 그대로 지나간다 | — |
| `GET /api/reviews/{id}` | `judgment.rule_effects`를 `decode(..., [])`로 풀어 돌려준다. 지금은 JSON 문자열 그대로다 | W-RULE (`review/api.py`) |
| `GET /api/learning/orgs` (새) | `{"orgs":[{"id":"t-alpha-it","name":"IT팀"}]}`. 권한은 후보 목록과 같다(`reviewer`·`rule_admin`·`operator`) | W-RULE (`candidates_api.py` + `candidates_store.py`) |
| `POST /api/learning/candidates` | 조건 키 허용 목록에 `text`를 더한다. `requester_org` 값이 tenant의 `Org.id`가 아니면 422 `{"code":"UNKNOWN_ORG","reason":"알 수 없는 조직: …"}` | W-RULE |
| `POST /api/learning/candidates/{id}/decision` (범위 수정 승인) | 같은 `UNKNOWN_ORG` 검사 | W-RULE (`learning/rules.py` `decide_candidate`) |

- 규칙 원문 확인용 원문 위치는 기존 `GET /api/requests/{id}/evidence/{span_id}`(`requestApi.evidence`)로 얻는다. 여기서 `attachment_id`를 받아 EvidenceViewer의 `source`를 정한다(없으면 `chat`). 새 API는 필요 없다.
- 조직 검사는 store 함수 `unknown_org_ids(tenant, scope) -> list[str]` 하나로 처리하고 두 경로가 함께 쓴다.

## 9. 화면 변경

**규칙 등록** (`pages/learning/Proposal.tsx`)

- "제안 범위" textarea를 조건 폼으로 바꾼다.
  - **원문 키워드**: 칩 입력. Enter나 쉼표로 추가하고 최대 20개다. 안내: "하나라도 포함되면 적용 · 대소문자·띄어쓰기 무시".
  - **요청 조직**: `GET /api/learning/orgs` 목록을 쓰는 `Select`. 값은 조직 ID다. 표시명은 `orgLabel`(`lib/labels.ts`에 추가)을 쓴다. 이름이 `ai|it|business`이면 AI팀·IT팀·현업으로 보여 준다(Review 화면의 매핑을 옮겨 공용화).
  - **판단 값**: 분류 항목과 값을 고른다(`field`, `op:"in"`).
  - **고급: 조건 JSON**: 접힌 영역이다. 폼이 만든 scope를 보여 준다. 직접 고치면 "JSON 직접 편집 중"으로 바뀌고 폼은 잠긴다. 신호와 업무 유형 조건은 여기서만 쓴다.
- 잘못된 예시(`{"requester_org": "IT팀"}`)를 지운다. 고급 영역 예시는 실제 조직 ID로 만든다(`{"all":[{"requester_org":"<목록의 첫 조직 ID>"}]}`).
- 섀도 검증과 승인·버전·게시 흐름은 바꾸지 않는다. 안내문을 하나 더한다. "키워드 규칙도 승인 → 섀도 검증 → 게시를 거쳐야 실행에 쓰입니다."

**규칙 요약** (`pages/learning/sections.tsx` `RuleSummary`)

- 범위를 사람이 읽는 문장으로 보여 준다. `scopeText(scope, orgs)`를 쓴다. 예: "원문에 ‘서버’ 또는 ‘VPN’ 포함 · 요청 조직 IT팀".

**결과 화면** (`pages/main/ResultCard.tsx`, R2)

- 분류 카드에 `ruleOverrides` 대상이면 다음을 보여 준다.
  - 배지 `규칙 적용 · R-LEAD_ORG-03 v1`
  - 줄 "모델 판단 AI팀 → 규칙 IT팀"
  - `matches`별 버튼 `규칙 근거 · ‘VPN’`: `requestApi.evidence`로 source를 얻은 뒤 EvidenceViewer를 `unitId`로 연다.
- 모델 근거 버튼 문구는 "모델 원판단(AI팀) 근거 열기"로 바꾼다.
- 요약 아래에 "적용된 규칙 n건"을 접은 목록으로 보여 준다. outcome은 used·conflict·blocked_by_invariant 가운데 `used`만 기본으로 보이고 나머지는 "자세히"에 둔다.
- 공용 조각: `frontend/src/lib/ruleEffects.ts`(`ruleOverrides`, `ruleLabel`), `frontend/src/components/RuleEffectBadge.tsx`.

**검토 화면** (`pages/Review.tsx`)

- "AI 원안과 검토 값"의 각 항목에 같은 배지와 "모델 판단 → 규칙" 줄을 단다.
- "신뢰 신호와 원문 근거"에 "규칙 근거" 인용을 더한다. `can_read_source`이면 단위 원문을 보여 주고, 원문 열기는 위와 같은 경로를 쓴다.
- 기존 `openSource`의 채팅 가정을 그대로 쓰지 않는다. `requestApi.evidence`로 `attachment_id`를 확인한다.

## 10. 기존 규칙·데이터 호환

- **기존 규칙.** text 조건이 없으므로 판정 결과가 같다. 새 필드 `target`·`source`·`matches`는 추가만 된다. 기존 `rule_effects` 소비자(학습 효과 집계 `learning/effects.py`, 규칙 상세 `application_count`)는 키를 더 읽지 않으므로 영향이 없다.
- **과거 Judgment.** 과거 `rule_effects`에는 `target`·`source`가 없다. 화면은 `source`가 없으면 `rule_version`(`R-X@1`)으로 `rule:R-X@v1`을 만든다. `target`이 없는 항목은 분류 카드에 붙이지 않고 "적용된 규칙" 목록에만 보여 준다.
- **정책 스키마.** `RuleReference.scope`는 `dict[str, Any]`이고 검증은 `validate_rule`에 맡긴다. 그래서 `policy-schema-v1`을 바꾸지 않는다.
- **배포 순서.** 예전 코드가 text 조건이 든 설정을 읽으면 `validate_rule`이 실패한다. 이때 `apply_rules`는 그 규칙을 `blocked_by_invariant`로 건너뛴다. 안전하게 실패하는 쪽이지만, **API와 worker를 같이 배포한 뒤에** 키워드 규칙을 게시하도록 운영 문서에 적는다.
- **재분석과 되돌리기.** 실행은 시작할 때 정책 버전을 고정하므로, 진행 중인 실행에는 새 키워드 규칙이 끼어들지 않는다. 규칙 중단과 되돌리기는 기존 `change_publication` 경로 그대로다.
- **하드코딩된 조직 이름.** `ORGANIZATIONS = {"AI팀","IT팀","현업"}`(분류값·action 값)은 이번 범위가 아니다. 조직 **ID**를 쓰는 곳은 `requester_org` 조건뿐이다.

## 11. 시험

- **단위** (`tests/unit/test_rule_keyword.py`)
  - 검증: 정상 형태. 빈 목록, 21개, 51자, 중복(`VPN`과 `vpn`), 키 오타, 원소가 문자열이 아님은 실패.
  - 정규화: 전각, 대소문자, 띄어쓰기, zero-width 문자. offset을 되돌리면 원문 조각이 키워드와 같은 글자인지 본다.
  - `apply_rules`
    - `lead_org` set 규칙이 `source`, `target`, `matches`와 함께 used로 기록된다.
    - `text_units`가 없으면 out_of_scope다.
    - AND 조합(text와 requester_org)을 확인한다.
    - 일치는 최대 5건이다.
  - `context_rules_for`: requester_org와 text 조합. 모델 값 조건이 들어간 context 규칙은 검증에서 실패한다.
  - 호환: text 조건이 없는 기존 규칙 묶음의 `apply_rules` 결과가 변경 전과 같다. 새 키 3개를 빼고 비교한다.
- **통합** (`tests/integration/test_rule_keyword_flow.py`, Neo4j 필요)
  - text와 조직 ID scope로 후보를 제안하면 201이다. 조직 이름(`IT팀`)으로 제안하면 422 `UNKNOWN_ORG`다.
  - `GET /api/learning/orgs`의 권한을 확인한다.
  - 섀도 검증이 text 규칙에서 표본 원문을 읽어 `changed_count > 0`이 된다.
  - 실행 1건(AI_MODE=mock)의 `rule_effects`에 matches가 있고, 판단 API와 검토 API가 decode된 배열을 돌려준다.
- **프론트**
  - `proposal.test.tsx`(수정): 키워드 칩, 조직 Select의 값이 ID인지, 만들어진 scope, 고급 JSON 전환.
  - `ResultCard.rules.test.tsx`(새): 배지, "모델 원판단" 문구, 규칙 근거 버튼.
  - `Review.test.tsx`(수정): 배지와 규칙 근거.

## 12. 구현 분할

두 워커 W-RULE(이 문서)과 W-LLM([LLM_ASSIST.md](LLM_ASSIST.md))이 병렬로 작업한다. `docs/readme/**`와 `scripts/readme/**`는 둘 다 건드리지 않는다.

### 12.1 W-RULE 소유 파일

| 구분 | 파일 |
|---|---|
| 백엔드 | `backend/ildongi/domain/rules.py`, `backend/ildongi/learning/apply.py`(export 추가), `backend/ildongi/learning/shadow.py`, `backend/ildongi/learning/candidates_api.py`, `backend/ildongi/learning/candidates_store.py`, `backend/ildongi/learning/rules.py`, `backend/ildongi/review/api.py` |
| 프론트 | `frontend/src/pages/learning/Proposal.tsx`, `frontend/src/pages/learning/sections.tsx`, `frontend/src/api/learning.ts`, `frontend/src/pages/Review.tsx`, `frontend/src/lib/labels.ts`, 새 파일 `frontend/src/lib/ruleEffects.ts`, `frontend/src/components/RuleEffectBadge.tsx` |
| 시험 | `backend/tests/unit/test_rule_keyword.py`, `backend/tests/integration/test_rule_keyword_flow.py`, `frontend/src/pages/learning/proposal.test.tsx`, `frontend/src/pages/main/ResultCard.rules.test.tsx`, `frontend/src/pages/Review.test.tsx` |
| 문서 | `docs/architecture/RULE_KEYWORD.md`(구현 결과 반영), `docs/architecture/LEARNING_RULES.md`(조건 문법 한 단락) |

### 12.2 공유 파일 (W-RULE이 먼저 고친다)

| 파일 | W-RULE 커밋 | 내용 | W-LLM이 그 뒤 하는 일 |
|---|---|---|---|
| `backend/ildongi/judgment/service.py` | **R1** `feat(rule-keyword): R1 …` | 82-87행을 `context_rules_for`로 바꾸고, `apply_rules` features에 `text_units`를 더한다. 이 두 군데만 고친다 | "글 다듬기" 단계 삽입 |
| `frontend/src/api/requests.ts`(`Judgment` 타입), `frontend/src/pages/main/ResultCard.tsx` | **R2** `feat(rule-keyword): R2 …` | `rule_effects` 타입, 분류 카드의 규칙 표시, 근거 문구 | summary·questions·llm·description |

- R1과 R2는 W-RULE의 **첫 두 커밋**이다. R1은 `domain/rules.py`의 `context_rules_for`·`text_matches`와 함께 올린다.
- R1·R2 뒤에 W-RULE은 위 공유 파일을 다시 고치지 않는다. 더 고쳐야 하면 W-LLM이 끝난 뒤에 고친다.
- W-LLM 소유 파일(`judgment/store.py`, `judgment/api.py`, `policy/service.py`, `Policy.tsx`, `Learning.tsx`, `main.py`, `pyproject.toml`)은 W-RULE이 건드리지 않는다.

### 12.3 W-RULE 수용 기준

```sh
make up                                   # Neo4j·Redis (통합 시험용)
cd backend && .venv/bin/pytest tests/unit/test_rule_keyword.py tests/integration/test_rule_keyword_flow.py -q
cd backend && .venv/bin/pytest -q         # 전체 회귀 (기존 규칙·섀도·학습 시험 그대로 통과)
make lint                                 # ruff + lint-imports
cd frontend && npx vitest run src/pages/learning src/pages/main src/pages/Review.test.tsx && npm run typecheck
cd frontend && npm run build
```

- 규칙 `{"text":{"contains_any":["VPN"]}} → lead_org set IT팀`을 후보 → 승인 → 버전 → 섀도 검증 → 게시까지 올린다. 그 뒤 "VPN 접속이 안 됩니다" 요청을 실행하면(AI_MODE=mock) 결과 화면 담당 조직이 IT팀이고, `규칙 적용 · R-…` 배지와 규칙 근거 버튼이 보이며, 버튼을 누르면 해당 원문 단위가 열린다.
- 조직을 고를 때 화면이 보내는 값이 `t-…-it` 형태의 ID다. 이름을 보내면 서버가 `UNKNOWN_ORG`로 거절한다.


## 13. 구현·검증 결과 (2026-10-06)

- R1: `context_rules_for`와 마스킹 전 전체 `text_units` 연결 후 코디네이터에 `R1 완료: judgment/service.py 수정 끝` 전송. R2: 결과 타입·규칙 배지·원문 버튼·모델 원판단 문구 구현 후 `R2 완료` 전송. 그 뒤 공유 3개 파일은 W-RULE이 재수정하지 않았다. 커밋 대신 메시지로 소유권을 인계했다.
- 후보 조건 폼·조직 목록/ID 검사·조건 요약, 규칙/context 판정, 섀도 원문 로드, 리뷰 API decode 및 표시를 구현했다. API 원문 비공개 처리에서 `text` 조건이 제거되는 버그는 코디네이터 추가 승인에 따라 `auth/policy.py`에서 규칙 본문의 `scope.all` 경로와 정확한 contains_any 형태에만 예외를 두어 수정했다. 일반 요청·근거·요약의 원문 `text`는 계속 비공개다.
- 규칙 전용 단위·Neo4j 통합: 24건 통과(`.data/rule-focused-final.log`). 이전 게시 버전만 text 조건을 가진 경우에도 기준 원문을 읽는 회귀를 포함한다. 원문 권한 없는 API의 조건 유실 RED 2건은 `.data/rule-redaction-red.log`, 수정 후 GREEN은 `.data/rule-redaction-green.log`에 남겼다. 추가 context·마스킹·섀도 회귀 39건도 통과했다.
- `make lint` 통과, 프론트 전체 최종 385건 통과(인수 범위 125건 통과), typecheck·build 통과. 공유 DB 병렬 실행에서는 graph fixture의 고정 `req_other` ID 충돌과 worker terminal ownership 실패가 발생했다. 코디네이터가 잔존 행 없음과 다른 워커의 전체 pytest 중지를 확인한 뒤 허용한 직렬 전체 재실행에서 **597건 통과·4건 skip**했다(`.data/rule-backend-serialized.log`).
- 브라우저: 정책 편집/게시 없이 규칙 학습 폼에서 `VPN 포함 → lead_org IT팀` 후보를 등록하고 자료 부족 인정→승인→섀도 검증→검증 완료→규칙 게시까지 수행했다. `.env`의 `AI_MODE=mock`을 변경하지 않았다. 기본 tenant `t-alpha`에 `R-LEAD_ORG-01@1`, Config v2를 게시했다.
- 게시 후 `VPN 접속이 안 됩니다.` 요청 `req_2d4190b43fe54dacb45bbbb650c282f7`, 실행 `run_509bdb2c2fbe43a395b0a080cbe5aa3c`에서 IT팀·규칙 배지·일치 VPN 버튼을 확인했다. 버튼 클릭으로 `esp_3050e45fb3cb4a588223cbb7a062351f` 원문 단위가 실제 열리고 anchor가 표시됐다. API 기록은 `.data/rule-browser-judgment.json`, 화면은 `.data/screens/rule-proposal.png`, `rule-published.png`, `rule-result.png`, `rule-source.png`다. 이 요청의 모델 원판단은 `판단 보류`, 규칙 적용 후는 `IT팀`, 단위 안 일치 범위는 `[0,3)`이다.
- Redis를 시작하지 않았고 기존 Neo4j 컨테이너를 사용했다. 런타임은 승인된 `.data/runtime.py restart api worker web`로 재시작했다. 브라우저 시연 규칙/요청은 재확인을 위해 유지했고, 시험용 `keyword_*` tenant는 fixture에서 정리한다. LIVE 분류 품질은 이번 mock 증거로 검증하지 않았다.
