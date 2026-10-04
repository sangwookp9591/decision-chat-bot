# Jev Triage 한국어 화면 녹화 — 최종본

- 최종 영상: `walkthrough.mp4` — **5분 39초, 10,141,825 bytes (약 10.1 MB)**. 무음·한국어 자막. 챕터: `chapters.md`.
- 재녹화: 저장소 루트에서 `bash scripts/demo/record.sh`
- 코드 변경 없이 API 9191, Vite 6491(/api→9191), tenant 제한 worker, collector, watchdog 직접 실행. OrbStack 공유 Neo4j 7687·Redis 6379는 중단하지 않음.
- tenant: `t-demo-20261004t100724z`; 교차 tenant 차단: `t-demo-20261004t100724zb`. bootstrap_dev와 같은 계정 구조의 기존 acceptance provision을 재사용하고 labeler·원문 권한을 전용 계정에 추가.
- JEV_MODE=live. 가상 회의실 업무 및 Markdown만 외부 모델에 전송. 로그인 비밀번호는 데모 전용이며 영상에 키/터미널/env 없음.
- Playwright Chromium recordVideo 장면별 녹화, 한국어 오버레이, ffmpeg H.264 CRF23. UI 대기·클릭 간 0.85~0.95초. 백엔드 결과는 조작하지 않음.
- 학습 사전 준비: 실제 요청 3건을 live 처리하고 공개 review API로 수정 승인; 화면 장면과 별도로 진행.
- 실행 종료 시 소유한 5개 프로세스만 정리. health.txt에 최종 공유 컨테이너 상태 기록.

## ffprobe 확인

```json
{
  "programs": [],
  "stream_groups": [],
  "streams": [
    {
      "codec_name": "h264",
      "width": 1440,
      "height": 900,
      "r_frame_rate": "30/1"
    }
  ],
  "format": {
    "duration": "339.200000",
    "size": "10141825"
  }
}
```

## 사용한 요청 ID

- req_1a5e8b45f1a74cad88cf6b441c78d289
- req_04e7deab030a4ce7a1232fe4d6e487f1
- req_5b07d6d88c9745f0b1716fc931d2febb
- req_cfe052770ae34b8b9de8d7ebfa726c4a
- req_e8e81ed1edce463385e92200b13372e3
- req_b7a5d33551c84d3481424c05dfb3177f

## 화면 측정과 문서 인용

{"start":1791108471765,"preliminary":1324,"final":null,"shared_summary_region_ms":1324,"final_measurement_note":"최초 측정 선택자가 잠정·최종 공용 영역을 감지했으므로 최종 표시 실측은 폐기함. provisional-badge 측정은 유효."}

화면 측정은 버튼 클릭 직전부터 DOM 표시까지이며 서버 처리시간과 다릅니다. 문서 예시 수치는 docs/architecture/ARCHITECTURE_OVERVIEW.html:210,218의 잠정 0.5–0.7초, 최종 1.3–1.6초로, 이번 실행 실측값으로 주장하지 않았습니다.

## 알려진 한계

- [심각도 낮음] 장면 9 — 데모에 실제 실패가 없어 실패→Trace 링크 시연 불가 — 실제 화면·manifest 기록 — 해당 조건 준비 후 재촬영 — 예상 규모 S


부수효과를 가진 장면은 실행 오류 시 무조건 전체 재실행하지 않습니다. 실패 장면은 화면에 부분 실패로 표시하고 manifest에 원인을 남깁니다. 제품 결함과 녹화 스크립트 오류는 구분하여 후속 재촬영해야 합니다.

## 종료 확인

소유한 API·worker·collector·watchdog·Vite 자식 프로세스 종료 확인.

```text
decision-chat-bot-neo4j-1 Up 9 hours (healthy)
decision-chat-bot-redis-1 Up 8 hours (healthy)
```

## 측정 정정

잠정·최종이 공유하는 summary 영역을 최종 완료로 잘못 감지하여 최종 표시 시각은 폐기했습니다. 잠정 배지 표시 1.32초는 클릭 이벤트부터 DOM 출현까지의 값입니다. 최종 영상 엔딩을 이 사실에 맞게 재촬영했으며 실제 제품 화면 장면 1–12는 바꾸지 않았습니다. 재실행 스크립트의 최종 표시 측정은 LIVE 배지 존재로 수정했습니다.

## 실행 기준과 재현 조건

- 실제 녹화 환경 HEAD: `a783292` (읽기 전용 `git rev-parse` 확인). 지시문 기준 `0da8b1e`로 checkout하지 않았고 현재 worktree를 사용했습니다. 이 작업에서 제품 코드는 수정하지 않았습니다.
- macOS, OrbStack, 기존 `backend/.venv`, `frontend/node_modules`, Playwright Chromium, ffmpeg/ffprobe 필요. 로컬 `.env`의 Jev·Neo4j 자격 증명을 서버만 읽으며 브라우저나 영상에는 노출하지 않습니다.
- 기본 실행은 새 UTC 디렉터리·새 tenant를 만듭니다. 9191/6491 포트가 점유됐으면 기존 프로세스를 종료하지 않고 실패합니다. 외부 watchdog webhook은 비활성화합니다.
- 동일 데이터가 매번 동일한 모델 판단을 보장하지는 않습니다. 실제 API 오류·장면 실패는 `manifest.json`에 남기고 영상 자막에서도 구분합니다.
- 최초 점검본 `../20261004T100019Z/README.md`의 실패 장면 4·5·8은 새 가상 요청으로 재촬영하여 모두 완료했습니다. 실패→Trace는 두 촬영 모두 실제 실패 표본이 없어 미시연이며 임의 실패 기록을 삽입하지 않았습니다.
- 규칙 학습의 수정 방향과 평가 라벨은 시연용 사람 결정입니다. 현업 정답 또는 분류 품질의 검증 결과로 사용하면 안 됩니다.
- 장면 8은 중단 완료 뒤의 정지 화면 꼬리를 잘라 40초로 편집했습니다. 승인·검증·게시·사용·중단 동작은 모두 포함됩니다. 측정 정정용 엔딩만 `scripts/demo/rewrite-ending.mjs`로 다시 촬영했습니다.

## 주요 실제 실행 증거

- 장면 4: `req_1a5e8b45f1a74cad88cf6b441c78d289`, AI 주관 `IT팀` → 사람 검토 `현업`; 원안·수정·검토자·시각·Config·결정 이력 표시.
- 장면 5: 실제 배정 20개 중 시작 가능한 업무를 `대기` → `진행`으로 전이. 선행 업무가 미완료인 카드의 차단 사유도 표시.
- 장면 8: `cand_8fcc507094e6868374ddec5c`, AI 필요성 수정 지지 3건; `R-DEMO-01@1`; `val_67a5ec68e27d42b7a990240e55f30ed7` 표본 5건·사람 결정 4건·부작용 0건; 게시 Config v2 → 적용 1건 → 중단 Config v3.
- 게시 후 요청: `req_b7a5d33551c84d3481424c05dfb3177f`; 범위 안 규칙 사용 1건. 효과는 화면에서도 표본 부족으로 표시.
- 장면 12: 새 다른 tenant 계정에서 첫 요청 URL 접근 시 ‘요청을 찾을 수 없습니다’ 표시, 요청 원문·판단 미노출.

## 촬영 중 발견 사항

- [심각도 낮음] `frontend/src/lib/labels.ts:107`, 장면 4 검토 화면 — 점수형 검토 필요도가 `111%`로 표시됨 — `outputValueLabel`은 확률뿐 아니라 모든 숫자 value에 100을 곱하고 `%`를 붙이며, `backend/jevtriage/domain/questions.py:62`의 review_signal은 score형임; 실제 녹화 DOM에도 ‘검토 필요도 · 점수형 111%’가 남음 — 출력 타입을 인자로 받아 score는 원래 점수와 기준 척도로, noul/confidence만 백분율로 표시 — 예상 규모 S.
- [심각도 낮음] 장면 9 — 실패→Trace 이동을 시연하지 못함 — 최초 및 재촬영 tenant에서 실제 실패 목록이 비어 있음 — 별도 전용 환경의 실제 실패 재현 요청을 준비해 이 장면만 추가 촬영 — 예상 규모 S.
- [심각도 낮음] 장면 13 측정 계측 — 최초 최종 결과 측정이 잠정 카드와 공용 summary 영역을 감지함 — 두 타이밍이 동일하고 코드 선택자 확인; 최종 값을 폐기하고 엔딩 재촬영 — 최종 LIVE 배지를 감지하도록 녹화 스크립트 수정 완료; 잠정 표시 1.32초만 실측으로 사용 — 예상 규모 S (완료).

## 최종 파일 검증

`ffmpeg -v error -i walkthrough.mp4 -f null -` 전체 디코딩 오류 0. 편집된 영상 03:34 프레임에서 규칙 중단 완료 뒤 비활성 동작 화면과 자막을 확인했습니다. 장면별 스크린샷과 `manifest.json`을 함께 보관합니다. JS 문법 검사·Python AST 검사·`git diff --check` 통과.
