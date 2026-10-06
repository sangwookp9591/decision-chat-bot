# 최종 회귀 검증 계약 (2026-10-05)

전체 브라우저·백엔드·프런트·장애 시험의 최종 증거는
[FINAL-REG 보고서](../../artifacts/review/final-regression/REPORT.md)에 기록한다.
최초 전체 실행과 실패 재검증을 구분하고, 파일·브라우저별 최신 판정을 합산한다.
serial 실패에 따른 후속 미실행은 별도로 재실행하기 전까지 통과로 세지 않는다.

이번 실행은 `scripts/e2e/run.py`의 독립 tenant·결정적 mock worker 준비 방식으로
API 11791·Vite 9191에서 Chromium·WebKit을 `--workers=1`로 실행했다.
실제 Decision AI 호출은 없으며 mock 결과를 모델 품질 증거로 취급하지 않는다.
접수·정책·검토·배정·규칙·그래프 경로는 실제 API와 Neo4j를 사용하고,
특정 UI 상태 회귀에 명시된 route fixture는 보고서에서 구분한다.

평가 화면의 불확실 답과 서버 허용값이 일치해야 한다. AI 필요성·개발 가능성의
“정보 부족”, 긴급도의 “판단 보류”도 유효한 평가 라벨이다.
전체 E2E가 발견한 422 회귀는 `f699b64`에서 수정됐으며,
[평가 라벨 계약](EVALUATION_LABELS.md)과 backend 회귀 시험을 따른다.

시험의 비동기 경계는 사용자 동작이 완료된 상태로 확인한다. 접수 시험은 HTTP 202를
확인하고, 일시적으로 나타나는 진행 heading·세 단계는 클릭 전 DOM 관찰을 시작해
실제 표시 여부를 기록한다. 최종 저장 결과와 근거 원문 assertion은 유지한다.
네 차례 평가 저장 및 네 가지 맵 필터/API 대조처럼 복합 시나리오는 전체 60초 예산을
명시하며, 제품 기대값과 개별 기능 assertion을 완화하지 않는다.

장애 시험은 브라우저 실행과 순차로 수행하고 OrbStack 전용 Neo4j 7688만 사용한다.
runner의 `finally`와 fault script의 cleanup trap이 소유 프로세스·컨테이너를 정리한
후 포트와 프로세스 목록을 확인한다. 공유 Neo4j 7687은 계속 유지한다.
원시 trace·스크린샷·영상·실행 데이터는 `artifacts/review/final-regression/`의
Git 제외 경로에 보관하고, 보고서만 추적한다.

최종 합산 결과는 브라우저 199 passed / WebKit 기능 미지원 1 skipped,
backend 532 passed / live 전용 1 skipped, frontend 단위 372 passed,
장애 11 passed이다. ruff·import 계약·typecheck·build도 통과했다.
최초 실패와 재검증을 포함한 판정 과정·전체 시간·정리 증거는 보고서에 보존한다.
