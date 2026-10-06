# 정책 E2E

실제 Neo4j와 API를 사용하는 Playwright 시나리오입니다. 테스트는 `policy_editor@t-alpha.dev`로 로그인해 잘못된 threshold 검증, 정상 게시, 버전 이력 조회, v1 기준 되돌리기를 수행합니다.

저장소 루트에서 실행합니다.

```sh
make up
cd backend
.venv/bin/python ../scripts/bootstrap_dev.py
.venv/bin/uvicorn ildongi.main:app --host 127.0.0.1 --port 8000
```

별도 터미널에서 프런트 테스트를 실행합니다.

```sh
cd frontend
npx playwright install chromium
npm run e2e
```

개발 계정 암호를 변경해 bootstrap한 경우 `ILDONGI_DEV_PASSWORD`에 같은 암호를 지정합니다. API 서버와 Neo4j는 테스트가 끝날 때까지 실행 중이어야 합니다.

## 화면 공용 입력 (screens-ui.spec.ts)
모니터링 기간(년·월·일·시·분 입력), 실행 관찰 검색 선택, 검토 대기·업무 필터를 확인합니다. 다른 tenant를 쓰면 `E2E_TENANT`로 지정합니다.

## 전체 Chromium·WebKit 회귀 실행

저장소 루트에서 `backend/.venv/bin/python scripts/e2e/run.py`를 실행한다.
공유 Neo4j는 켜 두고 API 11091·Vite 8491을 비워 둔다. 실행기는 새 tenant와
역할 계정·30건 목록 표본·실패 전용 tenant를 준비하고, tenant가 제한된 워커를
시작한 뒤 종료 시 소유한 프로세스만 정리한다. Docker Desktop이나 다른
개발 서버를 시작·종료하지 않는다.

- `AI_MODE=mock` 전용 fixture client는 분류·근거·업무 유형의 결정적 모델 응답만
  제공한다. 실제 Neo4j 저장, 정책, 검토, 배정, HTTP API, 브라우저는 제품 경로다.
  이는 모델 정확도나 live Decision AI 품질 증거가 아니다.
- rem-ui와 learning은 독립 tenant를 준비한다. source-viewer의 고정 노드 ID와
  규칙 ID는 tenant 접두사를 붙여 공유 DB의 기존 자료와 충돌하지 않는다.
- acceptance gates는 실제 자동 배정 후 DB에서 직접 읽은 관계를 API·UI와 비교한다.
  extension은 후보 생성·규칙 게시·적용·수명 주기 단계별로 실제 자료를 준비한다.
- 모든 Playwright 실행은 `--workers=1`이다. `A11Y_SHOT_DIR` 등 증거 경로를
  새 실행 디렉터리로 지정하여 기존 t23 PNG를 덮어쓰지 않는다.
- 기본 산출물은 `artifacts/review/e2e-all/<실행시각>/`의 JSON·로그·trace다.
  좁은 재현에는 뒤에 Playwright 인수를 붙인다. 예:
  `backend/.venv/bin/python scripts/e2e/run.py modal-stack --project=webkit`.
- WebKit의 LayoutShift PerformanceEntry 부재는 명시적 skip 사유다. 다른
  브라우저·단계에서 실행할 extension phase는 해당 단계 필터로 선택한다.
  계정·fixture 누락을 통과 또는 환경 skip으로 처리하지 않는다.

2026-10-05 전체 재실행과 live 한도 실행의 결과는
[`artifacts/review/e2e-all/REPORT.md`](../../artifacts/review/e2e-all/REPORT.md)를 참조한다.
