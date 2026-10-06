# README LIVE 재촬영 기록

- 촬영·검증일: **2026-10-06 (Asia/Seoul)**.
- 목적: 기존 README 화면의 옛 프로젝트 표시명 `Jev Triage`를 현재 제품 표시명 **일동이**, AI 표시명 **Decision AI**로 반영.
- 범위: `docs/readme/`의 WebP 12장, GIF, manifest, 이 보고서만 갱신. 제품 코드·촬영 파이프라인·루트 README의 기존 변경은 수정하지 않았으며 커밋·push 없음.
- 기존 `scripts/readme/README.md`, `run.py`, `seed.py`, `capture.mjs`, `optimize.py`, `verify.py`를 읽고 해당 파이프라인을 실제 실행했다.
- 격리: 전용 API **10491**, Vite **7791**, 새 tenant, tenant allowlist Worker, OS 임시 폴더 아래 독립 절대 `DATA_DIR`. `AI_MODE=live`는 촬영 프로세스 환경변수로만 적용했다. `.env`는 읽기만 했으며 API 키 값은 출력·보고·산출물에 남기지 않았다.
- 기본 서버 **8000/5173**은 중지하지 않았다. 공유 Neo4j·Redis 및 `office-meal-*`, `zivo-*` 컨테이너를 조작하지 않았다.

## 실제 요청과 결과

**LIVE 업무 요청 총 4건: seed 3건 + UI 1건.** 이후 map·learning 보완 촬영은 동일 tenant·요청·DATA_DIR를 재사용했으며 추가 LIVE 요청은 **0건**이다.

- API 로그의 `POST /api/requests` HTTP 202가 4건.
- 전용 journal의 `request_received`, `request_completed`, `worker_attempt_start`, `judgment_preliminary`, `judgment_committed`, `worker_run`이 각각 4건.
- seed는 LIVE mode 판단 3건을 확인한 뒤 수정 승인했다. 업무·수정 이력·학습 후보와 전용 조직 범위 규칙 초안을 실제 생성했으며 운영 게시하지 않았다.
- UI 요청의 타이핑·잠정·최종 상태를 실제 촬영했다. 최종 판단은 근거 1건, AI 불필요, 개발 가능성 정보 부족, 긴급도 판단 보류를 그대로 보여 준다. 응답이나 업무·지표를 꾸미지 않았다.
- 개인정보 없는 회의실 예약 가상 입력을 사용했다. 계정명·tenant·기술 ID는 촬영 DOM에서만 가림/생략했다. 보완 촬영은 비동기 렌더링에도 가림을 유지했으며 모델 기술 ID도 생략했다. 서버 저장 값은 변경하지 않았다.

## 실패 → 보완 → 통과

| 관찰·실패 | 보완 | 최종 확인 |
| --- | --- | --- |
| 기존 hero 이미지에 `Jev Triage`가 보임. 기존 `verify.py`는 이 이미지도 PASS하여 브랜드 검증을 대신하지 못함 | 실제 LIVE 환경에서 전체 장면 재촬영 | 최종 WebP 12장과 GIF 3개 프레임을 각각 직접 열어 옛 브랜드 부재, 일동이, LIVE 배지 확인 |
| 전체 원본 촬영 후 `optimize.py`가 `cwebp` 미설치로 실패 | 시스템에 webp 1.6.0 도구 설치 후 동일 PNG 원본으로 압축 재실행 | 추가 LIVE 0건, WebP·GIF 생성 성공 |
| 기존 map 확대 보기 촬영은 사이드바와 LIVE 배지를 프레임 밖으로 밀어냄. 모델 기술 ID도 노출 | 코디네이터 승인 후 같은 데이터로 map만 일반 보기·AI 필요성 노드 선택 상태로 재촬영 | 사이드바 일동이, live 배지, Decision AI와 실제 선택 경로 확인; 모델 ID 생략 |
| 기존 learning 가림은 tenant 치환 뒤 사용자 기술 ID가 부분 잔존. 비동기 React 렌더링 뒤 ID가 재등장하기도 함 | 데이터 렌더링 완료를 기다리고 사용자 ID를 tenant보다 먼저 생략; 촬영 DOM에서 변경 관찰로 가림 유지 | 최종 learning 이미지에서 계정명·tenant·기술 ID 가림 직접 확인 |
| 두 ego-browser 호출 사이 DPR 초기화로 보완 PNG가 1440×900; 해상도 assertion 실패 | 같은 호출 안에서 DPR 2 설정·촬영·PNG 헤더 치수 확인 후 공간 닫기 | 보완 원본 2880×1800 PASS; 원본 확대·이미지 내용 편집 없음 |

보완은 저장소 촬영 스크립트를 변경하지 않고 OS 임시 폴더의 실행 스크립트로 수행했다. 기존 파이프라인의 일반 실행만으로는 map 브랜드 프레이밍·학습 ID 가림을 보장하지 않으므로 다음 촬영에서도 육안 검수가 필요하다.

## 최종 검증

`backend/.venv/bin/python scripts/readme/verify.py`:

```text
PASS: links, 12 scenes + animation; 1,191,125 bytes
```

- 최종 정지 이미지 12장 모두 직접 열어 검수했다. GIF는 3개 프레임을 추출하여 각각 직접 열어 확인했다.
- 모든 이미지와 GIF 프레임에 `Jev`/`jev` 문자열이 육안으로 보이지 않는다. 데스크톱은 사이드바, 모바일은 상단에 표시된 동일 메뉴 브랜드가 **일동이**다.
- 모든 장면에 실제 환경의 `live` 배지가 보인다. 판단·모바일 채팅·GIF 최종 상태에는 **LIVE** 결과 배지도 보인다. `Decision AI`는 판단 맵·모바일 채팅·GIF 진행 상태에서 확인했다.
- WebP 10장 2880×1800, 모바일 2장 750×1800. GIF 960×600, 3프레임, 총 4.5초. 정지는 원본 @2x PNG에서 리사이즈 없이 WebP 품질 82로 압축했다.
- GIF만 960×600으로 줄여 실제 타이핑·잠정·최종 상태를 각 1.5초씩 표시한다. GIF 길이는 실제 응답 지연을 의미하지 않는다.

| 파일 | 실제 픽셀 | 바이트 |
| --- | --- | ---: |
| [hero.webp](hero.webp) | 2880×1800 | 71,948 |
| [judgment.webp](judgment.webp) | 2880×1800 | 99,454 |
| [review.webp](review.webp) | 2880×1800 | 97,428 |
| [tasks.webp](tasks.webp) | 2880×1800 | 81,026 |
| [map.webp](map.webp) | 2880×1800 | 100,148 |
| [learning.webp](learning.webp) | 2880×1800 | 120,852 |
| [evaluation.webp](evaluation.webp) | 2880×1800 | 103,964 |
| [monitoring.webp](monitoring.webp) | 2880×1800 | 73,104 |
| [policy.webp](policy.webp) | 2880×1800 | 86,310 |
| [dark.webp](dark.webp) | 2880×1800 | 90,816 |
| [mobile-chat.webp](mobile-chat.webp) | 750×1800 | 58,508 |
| [mobile-review.webp](mobile-review.webp) | 750×1800 | 44,698 |
| [progressive.gif](progressive.gif) | 960×600 | 162,869 |

**총 1,191,125 bytes.** 정지 장당 400KB, GIF 1MB, 전체 6MB 제한 통과. 기계 판독용 [images.json](images.json).

## 종료·한계

직접 시작한 API·Worker·Collector·Watchdog·Vite 프로세스를 모두 종료했다. 최초·보완 촬영 TaskSpace를 모두 닫았다. 기본 API 8000/Vite 5173은 최초와 동일 PID로 계속 LISTEN 상태이며 전용 포트 10491/7791은 비어 있다.

원본 PNG·journal·API 로그·DATA_DIR는 OS 임시 폴더 `ai-readme-*`에 로컬 보관한다. `.env`와 쿠키는 산출물에 저장하지 않았다. 전용 tenant의 실제 시연 기록은 남겼다. 절차는 [촬영 안내](../../scripts/readme/README.md)를 참고한다.

이번 작업은 브랜드 반영과 촬영 검증이다. 전체 백엔드·프런트 테스트, 장애 시험, 별도 LIVE 평가, G12 품질 승인·G13 운영 검증은 재실행하지 않았으며 **운영 배포 승인 아님**.
