# 데이터 처리와 보존

## Decision AI로 전송되는 정보

판단 서비스는 요청 텍스트, 추출된 첨부 텍스트 단위, 운영 기준 문장과 질문을 state로 구성해 Decision AI SDK에 전달한다. 첨부 파일 바이너리 자체가 아니라 지원 파서가 만든 텍스트가 대상이다. 요청에는 업무상 민감 정보가 들어갈 수 있으므로 live 호출은 외부 모델 처리임을 사용자에게 알리고 검증되지 않은 민감 실데이터 데모를 제한해야 한다. 데이터 처리 계약은 [Decision AI 계약](../architecture/AI_CONTRACT.md), 구성은 `backend/ildongi/judgment/`에서 확인한다.

## 마스킹과 로그

외부 Decision AI 호출 직전 요청 단위의 임시 토큰 표로 state의 `units[].text`, `chat_text`, 근거 `source_unit`, 업무 분해 state, `operating_guidance`를 마스킹한다. 기본 정책 `masking.enabled=true`이며 범주는 주민/외국인등록번호, 사업자등록번호, Luhn 유효 카드번호, 이메일, 국내 전화번호, 하이픈 구분 계좌번호 형태, IPv4, 비밀 키가 담긴 URL 쿼리, API 키 형태 및 긴 영숫자 토큰이다. 같은 값은 한 판단 요청에서 같은 토큰이 되고 토큰 표는 서버 메모리에서 요청 종료 후 폐기한다. `unit_id`와 원문 EvidenceSpan, 원문 화면 표시, 근거 위치는 바꾸지 않는다.

정책 편집자만 정책 게시 API로 `masking.enabled=false` 또는 범주 변경을 발행할 수 있고, 기존 정책 버전과 변경 사유가 감사 기록에 남는다. 비활성화 시 원문이 외부 모델로 전달되므로 운영 승인 없이 사용하지 않는다. 오탐은 업무 식별 문자열이 가려지는 형태로, 미탐은 사람 이름, 주소, 비정형 계좌·키, 분할된 문자열 등으로 나타날 수 있다. 이 탐지는 민감 정보 전부를 보장하지 않으므로 실제 민감 자료는 별도 검토 후 투입한다.

worker journal의 `external_masking` 기록과 Decision AI 판단 Trace에는 전송 전후 문자 길이, 치환 건수, 호출 건수만 남긴다. 원문과 전송 문자열, 토큰 표를 기록하지 않는다. 그 밖의 API/worker journal은 허용된 ID, 단계 종류, 시각, 상태 코드, 오류 분류, 소요시간 및 validity만 기록한다. 오류 로그·콘솔·스크린샷·증거 파일에 `AI_API_KEY`, 쿠키, 원문, 모델 payload를 복사하지 않는다.

## 저장 범위

Neo4j에는 요청·revision·판단·근거·검토·업무·정책과 운영 식별/상태가 저장된다. 업로드 원본은 `DATA_DIR/files/<tenant>/<sha256>`에 저장되고, journal은 `DATA_DIR/journal/`, 수집된 SQLite metrics는 `DATA_DIR/metrics/metrics.db`, 로컬 알림은 `DATA_DIR/alerts/` 아래에 둔다. Neo4j는 업무 상태의 기준 저장소이고 journal은 재생용 업무 큐가 아니다.

## 보존·삭제 상태

보존 기간과 자동 삭제, 사용자 삭제 요청 처리, 법적 보존, 백업 만료·파기 기간은 확정되지 않았다. 기간을 임의로 약속하지 않는다. 운영 결정이 필요한 설정 항목은 원본 파일, Neo4j 요청/첨부 메타데이터, journal, metrics SQLite, alerts 및 백업 각각의 보존 기간과 삭제 책임자다. 현 코드에 해당 보존 기간 설정이나 통합 삭제 절차는 없다. 삭제 정책이 승인될 때까지 민감 실데이터의 운영 투입을 제한하고, 백업도 원본과 같은 접근 통제를 적용한다.

### 개발용 보존 기본값과 정리 실행

`python -m ildongi.ops.retention --dry-run`은 tenant별 예정 건수를 출력하며 데이터를 바꾸지 않는다. 실제 실행은 `python -m ildongi.ops.retention` 또는 `make retention`이다. `make retention RETENTION_ARGS=--dry-run`으로 Make에서도 미리 볼 수 있다. 현재 활성 정책의 `retention` 설정을 사용하며, tenant 단위 점검은 `--tenant <tenant-id>`로 제한할 수 있다.

초기 개발 기본값은 Event 90일, Idempotency 30일, 만료 Session 7일 유예 후, LoginAttempt는 설정된 실패 창(기본 15분) 만료 후, journal 회전 파일 90일, metrics 원시 이벤트 90일이다. 이것은 **운영 확정 전 개발 기본값**이며 보존 약속이나 운영 승인 정책이 아니다. `PolicyConfig.retention`에서 기간과 삭제 배치 크기를 설정한다. 매 트랜잭션 최대 삭제 수는 설정 `batch_size`(기본 500)로 제한한다. journal 회전 파일은 metrics collector가 끝까지 수집한 offset을 확인할 수 있을 때만 삭제한다. 실행 요약은 journal에 남는다.

Event 정리 때 tenant EventCounter의 `retained_from_seq`를 갱신한다. SSE 소비자는 그보다 오래된 커서에 대해 snapshot 복구가 필요하다. 현재 SSE 라우터는 이 필드를 읽지 않고 삭제된 커서의 `created_at`도 찾지 못하므로, 이 개발 정리와 SSE의 오래된 커서 검출 계약은 아직 완전히 맞지 않는다. 운영에서 Event 보존 정리를 활성화하기 전에 SSE 라우터가 `retained_from_seq`를 검사하도록 통합해야 한다. Request, Judgment, Review, Task, RuleVersion, APPLIED, Correction, ConfigVersion 및 Audit 업무 기록은 이 정리 작업의 삭제 대상이 아니다. 원본 파일, 알림, 백업은 이 작업에서 삭제하지 않는다.
