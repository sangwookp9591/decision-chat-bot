# README 화면·실행 검증 기록

- 촬영·검증일: 2026-10-05 (Asia/Seoul)
- 범위: `README.md`, `docs/readme/**`, `scripts/readme/**`만 수정. 제품 코드, 공용 감사 경로, 다른 작업자의 서버는 변경하지 않음. 커밋·push 없음.
- 런타임: Python 3.14.6, Node 22.14.0, Docker Engine 29.4.0, Docker context `orbstack`.
- 전용 API 10491·Vite 7791, 새 tenant, `JEV_MODE=live`, tenant allowlist Worker, 독립 절대 DATA_DIR.
- 새 tenant에 실제 LIVE 요청 3건을 시드하고 3건 수정 승인하여 업무·수정 이력·학습 후보·범위 제한 규칙 초안을 생성. UI 촬영과 해상도 재촬영에서 요청 5건이 추가되어 총 8건이며, 규칙은 운영 게시하지 않음.
- 문서 화면은 모두 실제 제품 렌더링. 개인정보가 없는 가상 입력을 사용하고, 계정명·tenant·기술 ID만 캡처 DOM에서 가림/생략. 원본 응답·판단·업무·지표 변경이나 지연 주입 없음.

## 실패 확인 → 보완 → 통과

| 항목 | 수정 전 실패·관찰 | 보완 | 최종 검증 |
| --- | --- | --- | --- |
| README 계약 | `verify.py` 최초 실행 exit 1: 필수 화면 12장·GIF, Mermaid·OrbStack·G10/G12/G13·운영 배포 승인 아님 문구 누락 | 한국어 README 전면 개편, 실제 화면·설치·문서 색인 추가 | 상대 링크·장면·문구·용량·치수·GIF 길이 PASS |
| 잠정 흐름 캡처 | 클릭 wrapper 뒤 타이핑 selector 대기가 timeout; LIVE 최종 응답은 정상 | 실제 전송 직후 DOM 상태를 관찰하고 타이핑·잠정·최종을 캡처 | 세 상태 캡처 성공, GIF 4.5초 |
| 캡처 해상도 | `optimize.py`의 2880×1800 assertion 실패: screenshot wrapper는 1440×900 저장 | DPR 2 설정 후 `Page.captureScreenshot`으로 네이티브 PNG 저장 | 데스크톱 10장 2880×1800, 모바일 2장 750×1800 PASS |
| Mermaid | Node 단독 parse는 DOMPurify 환경 오류 | 기존 frontend jsdom을 연결한 검증 스크립트 추가 | 두 flowchart 문법 parse PASS |

## 실제 빠른 시작 확인

기존 의존성·`.env`를 재사용해 설치 상태를 검증했다. clone·가상환경 재생성·기존 `.env` 덮어쓰기는 하지 않았다.

- `docker --context orbstack info` 성공, `DOCKER_CONTEXT=orbstack make up` 성공(기존 Neo4j Running).
- `(cd backend && .venv/bin/python -m jevtriage.db.schema)` 성공.
- `backend/.venv/bin/python scripts/bootstrap_dev.py` 성공.
- `backend/.venv/bin/pip check`: No broken requirements found.
- README와 동일한 uvicorn·Worker·Collector·Watchdog·Vite 진입점을 전용 포트와 절대 DATA_DIR로 기동. `/api/health` → `{"status":"ok"}`, `/api/ready` → `{"status":"ready"}`, Vite → HTTP 200.
- 브라우저 로그인과 실제 LIVE 요청·검토 수정·학습 초안까지 확인. API 8000·Vite 5173 기본 포트는 공유 환경 충돌을 피하려고 이 실행에서 사용하지 않음.
- 백업·복원과 fault·LIVE 평가·Playwright 전체는 이번 문서 작업에서 재실행하지 않음. 관련 명령과 기존 절차·주의를 README에 보존했으며, 파괴적 장애 시험이나 별도 비용 발생 평가를 문서 검증에 포함하지 않음.

## 코드 검사

| 명령 | 결과 |
| --- | --- |
| `cd backend && .venv/bin/pytest -q` | **466 passed, 1 skipped**, 104.50초 |
| `.venv/bin/ruff check jevtriage tests` | **All checks passed** |
| `.venv/bin/lint-imports` | **6 kept, 0 broken** |
| `npm --prefix frontend run typecheck` | PASS |
| `npm --prefix frontend run test` | 최종 **40 files / 358 tests passed**, 24.20초 |
| `npm --prefix frontend run build` | PASS |
| `node scripts/readme/verify-mermaid.mjs …/mermaid.esm.mjs` | Mermaid 1·2 PASS |

최초 병행 프런트 전체 실행은 `Main.layout.test.tsx`의 마스킹 제목 버튼 탐색 1건 실패(357 passed)였다. 제품 코드 변경 없이 해당 파일 단독 재실행 18/18, 전체 재실행 358/358 통과했다. 일시적 실행 부하/시간 제한 가능성이 있으나 원인은 확정하지 않았고 최초 실패도 코디네이터에게 보고했다.

## 화면 장수·용량

정지 화면은 원본 @2x PNG에서 WebP로 압축했으며 리사이즈하지 않았다. GIF만 960×600으로 줄이고 실제 타이핑·잠정·최종 상태를 각 1.5초씩 표시한다. GIF의 재생 길이는 실제 모델 지연을 의미하지 않는다.

| 파일 | 실제 픽셀 | 바이트 |
| --- | --- | ---: |
| [hero.webp](hero.webp) | 2880×1800 | 86,642 |
| [judgment.webp](judgment.webp) | 2880×1800 | 113,168 |
| [review.webp](review.webp) | 2880×1800 | 125,472 |
| [tasks.webp](tasks.webp) | 2880×1800 | 81,792 |
| [map.webp](map.webp) | 2880×1800 | 147,788 |
| [learning.webp](learning.webp) | 2880×1800 | 140,850 |
| [evaluation.webp](evaluation.webp) | 2880×1800 | 104,664 |
| [monitoring.webp](monitoring.webp) | 2880×1800 | 75,034 |
| [policy.webp](policy.webp) | 2880×1800 | 86,832 |
| [dark.webp](dark.webp) | 2880×1800 | 107,228 |
| [mobile-chat.webp](mobile-chat.webp) | 750×1800 | 58,558 |
| [mobile-review.webp](mobile-review.webp) | 750×1800 | 50,594 |
| [progressive.gif](progressive.gif) | 960×600 | 172,784 |

**정지 이미지 12장 + GIF 1개, 총 1,351,406 bytes (1.35 MB).** 정지 장당 최대 147,788 bytes < 400KB, GIF 172,784 bytes < 1MB, 전체 < 6MB. 기계 판독용 [images.json](images.json).

## 한계·건너뛴 항목

- LIVE 결과는 해당 가상 사례의 실제 응답이다. 최종 카드의 근거 0건·정보 부족·판단 보류를 보기 좋게 바꾸지 않았다. 판단 맵도 실제 연결만 보여 주므로 비어 있는 계층이 있다.
- 작은 시연 표본은 G12 품질 승인이나 G13 운영 검증을 대신하지 않는다. G10/G12/G13 외부 대기와 **운영 배포 승인 아님**을 README에 명시했다.
- 제품 결함 수정은 담당 범위 밖이라 하지 않았다. `docs/architecture/*.md`도 이번 담당 파일 범위 밖이며 구조 변경이 없어 기존 문서에 링크하고 README Mermaid 요약만 갱신했다.
- 시연 원본 PNG·로그·DATA_DIR는 OS 임시 폴더에 로컬 보관한다. 비밀 `.env`, 쿠키, 외부 API 키를 README 산출물에 복사하지 않았다. 재촬영 절차는 [scripts/readme 안내](../../scripts/readme/README.md)에 있다.

## 종료 확인

직접 시작한 API·Worker·Collector·Watchdog·Vite 자식 프로세스 모두 종료했다. 촬영 TaskSpace를 닫았고 공유 OrbStack Neo4j·Redis는 계속 실행 중이다. 8191·5391 프로세스와 다른 작업자의 artifacts 경로에는 접근·변경하지 않았다.
