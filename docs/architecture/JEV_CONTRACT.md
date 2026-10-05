# Jev 계약과 실연동 기록

확인일: 2026-10-03 (UTC) · 상태: T02 실연동 확인, 제품 통합 전

이 문서는 T09 판단 클라이언트의 입력 계약이다. 제품 동작은 이 계약에 맞춰 모델 반환값을 보존하고, 자체 평가·분기 로직과 모델 신호를 구분해야 한다.

## 확인한 연결과 모델

- API는 `POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer <key>`, `Content-Type: application/json`이다. 본문 최상위 필수 필드는 `state`, `model`, `questions`다.
- `state`는 텍스트 또는 텍스트 기반 object/array이며, 이미지·오디오·비디오는 입력할 수 없다. Jev는 `state`를 한 번 받고 질문들을 각각 독립 평가한다.
- `questions`는 질문 ID → typed question 객체의 맵이다. 응답의 `answers`는 같은 ID로 결과를 돌려준다. 질문 ID는 애플리케이션 연결 키이며 추론에는 포함되지 않는다.
- 계정 모델 목록 조회 성공. 이번 목록 응답에는 `jev-latest`, `jev-preview` alias가 있었다. 요청에 `jev-1.13.0`을 명시했고 실제 반환 `model`도 `jev-1.13.0`이었다. 제품 계약은 alias 이동에 따른 판단 변화 추적을 위해 이 버전을 고정한다. 버전 변경은 평가 표본으로 별도 검토한다.
- 응답 최상위 필수 필드는 `model`, `answers`, `usage`; usage는 `input_tokens`, `output_tokens`를 포함한다. 성공 응답에는 호출의 응답 모델 ID와 질문별 typed answer를 보존한다.
- 현재 모델 문서에는 64k total token context, `state`와 가장 긴 단일 질문 합계 32k 제한, 100K tokens/s 및 80 requests/s 한도가 게시되어 있다. 한도는 변동 가능하다고 공식 문서가 명시하므로 운영 설정에 상수로 고정하지 말고 429와 응답 헤더를 처리한다. 본 입력은 텍스트만 전송했다.

실제 probe: “SAP에서 내려받은 매출 CSV를 월별로 집계해 화면에 보여 달라.”로 AI 필요성(Choice), 개발 가능성(Choice), 긴급도(Choice), 주관 조직(Choice), 검토 신호(Score), AI팀·IT팀·현업 참여 필요성(Noul)을 한 번에 물었다. 응답 모델 `jev-1.13.0`, usage 1,189 input / 272 output tokens, 판단 호출 지연 205.1 ms였다. 값은 검증 증거 [response-20261003T070311Z.json](../../artifacts/validation/t02/response-20261003T070311Z.json)에 있다. 예시 응답은 제품 품질 보증이나 자동 배정 허용 근거가 아니다.

## 질문과 응답 스키마

모든 타입에 `type`과 `instructions`가 필요하다. `instructions`는 string/object/array를 허용한다. 단일 질문에 명확히 초점을 두며 서로 독립인 질문은 같은 요청에 모아 보내도 된다.

| 타입 | 요청 필드 | 응답 필드 | 해석 |
| --- | --- | --- | --- |
| Choice | `type: "choice"`, `instructions`, 필수 `criteria` map(option → 설명/null; 최대 255 옵션) | `type`, `choice`, `probabilities`(모든 옵션, 합 1), `confidence`(0–1) | `choice`는 최댓값 옵션. `confidence`는 최댓값이 균등 분포보다 얼마나 뾰족한지 요약하며 정확도 보장이 아니다. |
| Score | `type: "score"`, `instructions`, 필수 순서형 `criteria` 배열(2–10개) | `type`, `score`, `legend`, `probabilities`, `confidence` | 각 수준은 배열 인덱스 0부터 시작한다. `score`는 각 수준 인덱스의 확률 가중 평균이라 두 수준 사이 값이 가능하다. `legend`는 숫자 수준을 설명에 연결한다. 신뢰도와 전체 분포를 함께 해석한다. |
| Noul | `type: "noul"`, `instructions`, 선택 `criteria: {true, false}` | `type`, `noul`(0–1) | `noul`은 명제가 참일 확률이다. 0.5 근처는 불확실성이다. 별도의 `confidence` 필드는 없다. |

**혼동 금지:** Choice/Score의 `confidence`는 타입별 probability 분포를 요약한 신뢰 신호다. Noul의 `noul`은 “예”의 확률 자체다. Noul 값 0.9를 Choice confidence 0.9와 같은 의미로 저장하거나 자동 배정 임계치에 그대로 대입하지 않는다. 신뢰도는 자체 평가 데이터에 맞춰 보정·정책화하며 결과 정확도의 보증으로 설명하지 않는다.

## 오류와 처리 계약

| HTTP | 공식 의미 | 제품 처리 권고 |
| --- | --- | --- |
| 401 | API 키 누락/잘못됨 | 인증 설정 오류로 분류. 재시도하지 않고 키 값은 절대 로그하지 않는다. |
| 422 | 본문 검증 실패. 오류 본문은 문제 필드를 가리킨다. | 요청/스키마 오류로 분류. 자동 재시도하지 않고 필드 수준 진단을 키·원문 없이 남긴다. |
| 429 | 계정 rate limit 초과 | `Retry-After`가 있으면 따르고 지수 backoff. 시도 횟수와 전체 호출 deadline을 제한한다. |
| 529 | 서비스 일시 과부하 | 429처럼 제한된 backoff 재시도. 예산 소진 시 실패로 보존한다. |
| 연결/읽기 timeout | HTTP 상태가 없을 수 있음 | timeout 유형과 attempt 지연을 남기고 전체 deadline 안에서 제한 재시도. 호출 결과가 불명확할 수 있으므로 idempotency를 가정하지 않는다. |

이 probe에서 실제 `401`(의도적으로 틀린 임시 키)과 `422`(Choice `criteria`를 잘못된 빈 배열로 전달)를 각 1회 확인했다. 응답 상태와 비민감 오류 본문은 증거 JSON에 기록했다. `429`, `529`, timeout은 발생을 강제로 유도하지 않았으며, 격리된 저한도 계정/네트워크 fault 환경에서만 검증할 것을 권고한다. 제한 초과 응답을 인위적으로 유발하면 실제 계정 이용에 영향을 줄 수 있다.

## SDK와 HTTP 선택

T09의 기본 선택은 공식 Python SDK `typesafe-sdk==0.7.2`이다. 같은 프로젝트 코드에서 typed `Choice`/`Score`/`Noul`, typed 응답, 모델 목록 조회를 제공하고 `api_key=`로 기존 `JEV_API_KEY`를 명시 전달할 수 있었다. SDK가 `TYPESAFE_API_KEY` 기본 환경변수에 기대지 않도록 클라이언트 생성자에 명시한다. 해당 SDK를 버전 고정하고 업그레이드 때 계약 증거를 다시 만든다.

HTTP는 스키마 오류 같은 경계 동작을 확인하거나 SDK가 아직 표현하지 않는 API 기능이 필요할 때만 보조 경로로 쓴다. SDK 기본 재시도에 무제한으로 맡기지 말고 `RetryPolicy`의 재시도 수·backoff·timeout을 설정한다. 제품은 전체 120초 판단 deadline 안에서 429/529/일시 네트워크 오류에 제한 재시도(예: 최대 2회, 지수 backoff, Retry-After 우선)를 권고한다. 401/422는 재시도하지 않는다. 120초는 PRD의 최초 판단 기준과 맞춘 상한 제안이며 실제 동시 부하·p95를 T25에서 측정해 조정해야 한다. 디버그 SDK 로깅은 요청/응답 body를 기록하므로 운영에서는 끄고, 키·원문·전체 state를 로그하지 않는다.

## 확인 기록

| 날짜 | 항목 | 방법 및 결과 | 미확인/제한 |
| --- | --- | --- | --- |
| 2026-10-03 | 공식 문서 계약 | Introduction, API, Models, Python SDK, Primitives의 Choice/Score/Noul, Confidence, SDK Usage 확인 | 제공자 한도는 변경될 수 있음 |
| 2026-10-03 | SDK 설치 | 저장소 밖 `/tmp/jev-t02-venv`에 설치, `typesafe-sdk 0.7.2`; Python 3.14.6 | 배포 의존성/lock 반영은 T01/T09 소유 범위 |
| 2026-10-03 | 모델 목록/실제 판단 | `scripts/jev_probe.py`; 기존 `.env`의 키를 메모리로 읽고 `api_key=`로 전달; 목록과 한국어 판단 성공 | 한 업무 문장만 확인. 비영어 품질은 별도 표본 평가 필요 |
| 2026-10-03 | 응답 구조·사용량·지연 | model/8 answers/usage 존재 확인; 1,189 input, 272 output; 205.1 ms | 단일 호출 지연은 SLO 측정이 아님 |
| 2026-10-03 | 401 / 422 | 실제 HTTP 오류 경로 각 1회 확인 | 429/529/timeout은 미실행, 방법만 기록 |
| 2026-10-03 | 제품 동작 | T02 스크립트는 계약 probe이며 애플리케이션 통합은 아님 | 제품 재시도, 검증, 영속 저장·Trace, G03는 T09/T10에서 확인 |

### 공식 출처

- [Introduction](https://docs.typesafe.ai/introduction)
- [API reference](https://docs.typesafe.ai/api)
- [Models](https://docs.typesafe.ai/models)
- [Python SDK](https://docs.typesafe.ai/sdk/python) 및 [Python SDK Usage](https://docs.typesafe.ai/sdk/python/usage)
- [Primitives](https://docs.typesafe.ai/primitives), [Choice](https://docs.typesafe.ai/primitives/choice), [Score](https://docs.typesafe.ai/primitives/score), [Noul](https://docs.typesafe.ai/primitives/noul), [Confidence](https://docs.typesafe.ai/confidence)

## 외부 전송 마스킹 경계 (FIX-QAC, 2026-10-05)

일반 판단과 context 규칙의 섀도 재판단은 공용 `judgment.masking.MaskingClient`를 사용한다. state의 채팅·근거 단위·근거 검증·운영 가이드뿐 아니라 새로 추가된 중첩 문자열과 질문 설명도 같은 토큰 표와 잠금으로 복사·마스킹한다. 질문 ID와 criteria의 키는 응답 계약을 유지한다. 내부 원문은 수정하지 않으므로 근거 영속화는 원문·위치를 보존한다. 일반 판단은 실행 고정 정책의 마스킹 설정과 세션을, 섀도는 검증 기준 정책의 설정을 사용한다. 섀도 호출 제한·사용량 집계는 마스킹된 호출에 적용한다.

`JevClient.ask` 자체에도 같은 공용 마스킹 구현을 적용하여 향후 직접 호출 경로의 기본 마스킹을 보장한다. 서비스에 주입한 테스트/대체 클라이언트도 공용 래퍼를 거친다. SDK의 `system_one` 전송은 `jev_client.py` 한 곳으로 제한하며 제품 시험이 이 경계를 검사한다. `masking.enabled=false`와 categories 정책은 기존 동작을 유지한다.

회귀 시험: `tests/integration/test_qac_regressions.py`는 일반·섀도의 실제 전체 모델 페이로드에서 이메일·전화·주민번호·Luhn 카드·런타임 조합 키 패턴 표본의 원문이 모두 0건임을 확인한다. `tests/unit/test_qac_external_boundary.py`는 직접 Jev 전송, 미래 중첩 state 및 질문 설명의 같은 경계를 검증한다. 실제 외부 API는 호출하지 않는다.
