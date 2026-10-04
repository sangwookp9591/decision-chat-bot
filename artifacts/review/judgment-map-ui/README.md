# 입체 판단 맵 재디자인 (UX-MAP) 검증

- 환경: API 9491 · vite 6791(임시 설정, `/api` → 9491) · 테넌트 `t-ux3` · `JEV_MODE=live` 워커 `--tenant t-ux3`. 데이터는 `frontend/e2e/source-viewer/seed.py` 방식의 저장 노드(규칙 R-UX-03 v1~v3, 5계층 10노드·9연결). 라이브 Jev 판단 1건 생성은 하지 않았다(아래 "건너뜀").
- 스크린샷: `after-{chromium,webkit}-{1440,960,375}-{before-select,selected}.png`. 이전 화면은 `before-chromium-1440-selected.png`, `before-375.png`(browser-exploration에서 복사). 재생성: `node shoot.mjs . after`.
- 페이지 가로 넘침: 6개 조합 모두 0px.
- 동작 확인(`check.mjs`, Chromium): 노드·연결 수가 API와 일치(10/9), 화면 노드 ID가 API 부분집합, 업무 단계 선택 시 경로 노드 4·경로 선 4, Esc 해제, 목록 보기 화살표·Enter 상세.

| 참고 이미지 요소 | 반영 | 확인 |
|---|---|---|
| 어두운 무대(near-black, 점 그리드·비네팅) | `.jm-stage` 고정 토큰, 점 그리드 + 비네팅 | after-*-1440 |
| 기울어진 판(등각) | `rotateX(38deg)` + 판 `skewX(-22deg)`, 반투명 슬래브 | 동일 |
| 깔때기(아래로 좁아짐) | 판 폭 920→520 | 동일 |
| 계층 숫자·이름·설명 | 판 하단 왼쪽 큰 숫자+이름, 오른쪽 설명 | 동일 |
| 빈 계층 얇은 판 | 높이 76, 한 줄 안내 | 동일 |
| 평행사변형 타일·계층 색 | 판과 같은 skew, 근거 회백/가설 라벤더/판단 남보라/적용 녹색/단계 어두움, 종류 칩 | 동일 |
| 연결선 점선·선택 경로만 밝게 | 가는 점선, 경로 흰색 점선+글로우, 실제 타일 가장자리 좌표 | selected |
| 선택 글로우·흐림·흰 점 | 흰 테두리+글로우, 비경로 opacity .3, 경로 점 | selected |
| 버전 탭+변경 요약 | 왼쪽 위 탭(되돌림/운영 중/검증 중 실제 상태), 요약 한 문장 | after-*-1440 |
| 확대율·+/−·전체 보기·크게 보기 | 왼쪽 아래 | 동일 |

## 건너뜀·한계
- 라이브 Jev 판단·검토 수정·규칙 게시 생성은 시간상 생략하고 저장 노드 시드로 5계층을 채웠다. 기존 `e2e/judgment-map.spec.ts`는(t-alpha 라이브 시드 필요) 실행하지 않았고 선택자(`.jm-node`·`.jm-line`·`jm-zoom-pct`·`.is-path`·`.jm-item`)는 유지했다.
- WebKit은 스크린샷만, 동작 확인은 Chromium만.
