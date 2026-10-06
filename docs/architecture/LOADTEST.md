# T25 개발 부하 시험

`make load`는 별도 Compose 프로젝트 `ildongi-t25`의 Neo4j(HTTP 7490, Bolt 7690), 전용 데이터 디렉터리, API 2 workers(8125), `t-alpha`만 처리하는 worker(동시성 10), collector를 시작한다. 종료 시 이 프로세스와 전용 컨테이너를 정리한다. 기존 개발 DB와 API는 사용하지 않는다.
측정 후 Neo4j 런타임 데이터와 가상 첨부 원본은 정리하고, 원시 journal·collector DB·CSV·Run snapshot은 산출물에 유지한다.

실행 전 `make up` 및 `make test`로 일반 회귀를 확인한다. 실제 Decision AI 키는 저장소 `.env`에서 설정 모듈이 읽으며 러너는 키를 출력하거나 산출물에 기록하지 않는다. 부하 입력은 가상 매출 집계 문장과 생성된 PDF·DOCX·MD 파일이다. 목표 비율은 텍스트 50%, PDF 25%, DOCX 15%, MD 10%이며 일부 입력에 20,000자 근처의 텍스트 또는 긴 첨부를 포함한다.

5분 예열에서 10개 가상 사용자가 각자 접수→최초 판단 완료/120초 실패를 기다리는 폐쇄 루프를 실행한다. 예열 처리량과 성공 실행의 Decision AI 호출 기록을 이용해 30분 예상 호출 수를 `warmup_estimate.json`에 남긴다. 이어 30분 측정 동안 같은 10개 루프와 SSE 20개 연결을 유지한다. Decision AI 호출 기록 25,000회 또는 관측된 최종 429 오류 비율 5% 초과 시 중단 사유를 남긴다. 클라이언트는 SSE 연결을 주기적으로 끊고 재연결한 뒤 snapshot 조회 시각을 기록한다.

각 실행의 `artifacts/validation/t25/<UTC timestamp>/`에는 환경 manifest, 클라이언트·SSE 원시 CSV, 독립 journal/collector, Run·RunStep 상태와 Decision AI usage, collector 정의를 재사용한 계산 결과와 한국어 보고서를 둔다. 최초 판단 실패는 120초 표본으로 계산한다. 가용성은 유효 접수·조회 호출, 판단 성공률은 첫 적격 요청을 분모로 사용한다. 미확정/누락 또는 충분하지 않은 표본은 통과로 판정하지 않는다. 운영 30일 SLO 달성과는 별도로 판정한다.

현재 제품 Run의 usage는 성공한 Decision AI 결과의 호출 시도와 토큰을 기록한다. 실패한 SDK 내부 시도와 재시도 후 복구된 429 응답의 정확한 수는 기록하지 않으므로 호출 총계는 이 경우 하한이다. 이 제한은 결과 보고서에 명시한다.

## FIX-SSE 보조 측정

tenant별 공유 폴링 변경은 `T25_OUTPUT_ROOT=artifacts/validation/t25-sse`, `T25_COMPOSE_PROJECT`, `T25_NEO4J_HTTP_PORT`, `T25_NEO4J_BOLT_PORT`, `T25_API_PORT`로 전용 경로·프로젝트·포트를 지정한 `loadtest/run.sh --warmup 120 --duration 600 --settle 0 --ai-call-cap 8000` 실행으로 비교한다. VU 10개, SSE 20개, 입력 비율과 live Decision AI는 T25와 같다. 기존 30분 공식 판정을 교체하지 않으며 보조 측정의 10분 길이 때문에 `analyze.py`의 30분 게이트는 통과 판정으로 해석하지 않는다. 실제 지연 분포와 이벤트 조회 질의 수의 비교 방법·제한은 해당 실행의 `REPORT.md`에 기록한다.

2026-10-03 실측 결과는 [`20261003T101333Z/REPORT.md`](../../artifacts/validation/t25/20261003T101333Z/REPORT.md)에 있다. 5분 예열 뒤 30분 측정에서 유효 요청 2,829건과 SSE 20개를 처리했고 개발 성능 판정 13/13을 통과했다. 1건의 Decision AI 500 계열 실패는 최초 판단 실패 및 120초 지연 표본에 포함했다. SSE 상태 전달 p95는 2,000ms로 목표 경계다. 이 증거는 연속 30일 운영 SLO 또는 T24 품질 게이트 완료를 뜻하지 않는다.
