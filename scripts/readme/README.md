# README 화면 재촬영

저장소 루트에서 실행합니다. 기존 Neo4j·Redis는 OrbStack에서 실행 중이어야 하고 `.env`에는 실제 `JEV_API_KEY`가 있어야 합니다. 제품 응답 모킹·판단 변경은 하지 않습니다.

```sh
# Python/Node 의존성은 루트 README의 설치 절차 사용
# 추가 이미지 도구: cwebp(libwebp), Pillow, ego-browser
backend/.venv/bin/pip install Pillow
backend/.venv/bin/python scripts/readme/run.py
backend/.venv/bin/python scripts/readme/verify.py
```

- API **10491**, Vite **7791**을 사용합니다. 점유된 포트를 발견하면 기존 프로세스를 건드리지 않고 중단합니다.
- `scripts/demo/provision.py`로 새 tenant와 역할별 계정을 준비합니다. Worker는 `--tenant`로 해당 tenant만 처리합니다.
- `seed.py`는 실제 LIVE 판단 3건을 수정 승인해 업무와 학습 후보를 만듭니다. 규칙은 전용 조직 범위의 초안으로만 생성하며 운영 게시하지 않습니다.
- `capture.mjs`는 ego-browser에서 실제 UI를 조작합니다. 채팅 요청 1건을 추가하고 타이핑·잠정·최종 상태, 검토·업무·판단 맵·학습·평가·모니터링·정책·다크·모바일을 촬영합니다.
- 데스크톱 **1440×900 @2x** → **2880×1800 PNG**, 모바일 **375×900 @2x** → **750×1800 PNG**입니다. `Page.captureScreenshot` CDP 호출로 CSS 픽셀 축소를 방지합니다.
- 계정명은 CSS로 가리고, 화면 내 기술 ID와 시연 tenant 문자열은 촬영 DOM에서만 생략 표시합니다. 결과·업무·지표의 실제 값은 바꾸지 않습니다.
- PNG 원본·API/Worker 로그·데이터는 OS 임시 폴더 `jev-readme-*`에 남습니다. `.env` 및 세션 쿠키는 저장하지 않습니다. 로컬 경로는 시작 시 출력됩니다.
- `optimize.py`는 WebP 품질 82로 압축하고 3개 실제 상태를 1.5초씩 이어 **4.5초 GIF**를 만듭니다. GIF는 시간 압축된 상태 소개이며 실제 지연을 주장하지 않습니다.
- `docs/readme/`에는 최종 WebP 12장·GIF 1개와 용량 manifest만 남습니다. 정지 이미지 장당 400KB, GIF 1MB, 합계 6MB 제한을 초과하면 실패합니다.
- 성공 시 촬영 TaskSpace를 닫습니다. 실패 시 동일 TaskSpace에서 원인을 확인하고, 새로운 LIVE 요청을 불필요하게 만들지 마세요. `captureSpace`는 `/tmp/jev-readme-session.json`에 기록됩니다.
- 종료 시 직접 시작한 API·Worker·Collector·Watchdog·Vite만 종료합니다. 공유 Neo4j·Redis를 중지하지 않습니다. 전용 tenant의 시연 기록은 남습니다.

## 검증

`verify.py`는 README 상대 링크·이미지 존재와 필수 장면·용량·치수·GIF 길이를 검사합니다. 최초 실행은 이미지 13개와 Mermaid·OrbStack·게이트 문구 누락으로 실패했고, 작업 완료 후 통과해야 합니다.

Mermaid 문법은 임시 디렉터리에 설치한 `mermaid`의 `parse()`로 검사할 수 있습니다. 저장소 의존성은 변경하지 않습니다.

```sh
npm install --prefix /tmp/jev-readme-mermaid --no-audit --no-fund mermaid@11
node scripts/readme/verify-mermaid.mjs /tmp/jev-readme-mermaid/node_modules/mermaid/dist/mermaid.esm.mjs
```

실제 실행 결과와 알려진 한계는 [촬영 보고서](../../docs/readme/REPORT.md)를 확인하세요.
