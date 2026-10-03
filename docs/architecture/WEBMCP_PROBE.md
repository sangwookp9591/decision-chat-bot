# WebMCP 호환성 사전 확인 (T00)

확인일: 2026-10-03 (Asia/Seoul)

## 공식 초안과 API

[WebMCP Draft Community Group Report](https://webmachinelearning.github.io/webmcp/)는 2026-10-02 발행본이다. W3C 표준 트랙이 아닌 커뮤니티 그룹 초안이며 변경 중이다. 웹 페이지가 AI 에이전트에 JavaScript 도구를 노출하는 규격이다.

현재 초안의 imperative API는 `document.modelContext`이며 주요 메서드는 `registerTool(tool, options)`, `getTools(options)`, `executeTool(tool, input)` 및 `unregisterTool(name)`이다. HTML 폼 기반 declarative API도 정의되어 있다. `navigator.modelContext`와 `provideContext`는 초안에서 찾지 못했다. 도구 호출 주체는 브라우저 내장/호스팅 agent(확장 포함), 외부 AI 플랫폼의 agent, 접근성 기술 등이며 페이지가 호출 에이전트를 자체 제공하는 규격은 아니다.

## 공식 Chrome 자료의 브라우저 조건

Chrome 공식 [WebMCP 개발 문서](https://developer.chrome.com/docs/ai/webmcp)는 Chrome 149부터 Origin Trial 참여가 가능하다고 안내하고, 로컬 개발은 `chrome://flags/#enable-webmcp-testing` 활성화 후 재시작하도록 설명한다. [Chrome DevTools for agents 문서](https://developer.chrome.com/docs/devtools/agents/webmcp-debugging)는 Chrome 149 이상과 Origin Trial 또는 WebMCP 플래그가 필요하다고 하며, DevTools agent로 도구 목록과 실행을 점검할 수 있다고 설명한다. Chrome 문서의 Model Context Tool Inspector 확장도 수동 호출 방법으로 제시되어 있다. Chrome 문서는 기능이 기본 활성화되지 않으며 로컬 개발·테스트 기능임을 명시한다.

## 이 머신의 확인 결과

| 항목 | 결과 |
| --- | --- |
| 설치 브라우저 | `/Applications`에서 Google Chrome만 발견. 버전 명령 출력 `Google Chrome 154.0.8037.97`; 앱 프레임워크 경로 버전은 `154.0.8037.58`. Edge·Canary는 발견되지 않음 |
| 자동화 | Node.js v22.14.0. 현재 저장소 기준 Playwright 모듈은 설치되지 않음 |
| 지원 모드 | `probes/webmcp/run_probe.sh enabled`는 Chrome headless에 `--enable-features=WebMCP`를 전달하도록 작성. 최초 실행에서는 `document.modelContext` 감지, 도구 등록과 `getTools` 발견 결과가 DOM에 기록되었으나 재실행 결과가 일관되지 않았고, `executeTool`을 통한 안정된 결과 증거는 확보하지 못함 |
| 미지원 모드 | `probes/webmcp/run_probe.sh unsupported`는 `--disable-features=WebMCP`로 실행. 저장된 [chrome-unsupported.html](../../artifacts/validation/t00/chrome-unsupported.html)에서 `data-webmcp="unsupported"`와 일반 페이지 미지원 안내 확인 |
| 외부 호출자 | Inspector 확장, 사용 가능한 브라우저 agent 또는 DevTools agent를 이 실행에서 연결하지 못함. 실제 브라우저 agent 호출 증거 없음 |
| 판정 | **차단**. 실제 지원 환경의 안정된 도구 등록·호출과 agent 호출 증거가 부족함 |

probe는 읽기 전용 `probe.echo` 도구 하나를 실제 API가 감지될 때에만 등록한다. 모의 API 객체는 만들지 않는다. 브라우저가 미지원이어도 제목·설명·안내를 표시하는 일반 HTML 페이지로 동작한다.

증거 파일은 `artifacts/validation/t00/`에 둔다. `chrome-headless.html`은 재실행 중 완료 상태가 DOM에 반영되기 전 저장된 덤프라 성공 증거로 취급하지 않는다. 브라우저 진단 stderr는 별도 파일에 보존한다.

## T20 권고

T20은 실제 Chrome 149 이상에서 `chrome://flags/#enable-webmcp-testing`을 켜고 재시작하거나 Origin Trial이 유효한 환경에서 다시 확인해야 한다. 안정된 등록/발견/`executeTool` 결과를 기록하고, Chrome DevTools for agents 또는 Chrome 공식 Inspector 확장 등 실제 agent 호출 주체로 `probe.echo`를 호출해 결과를 저장한다. 동일 환경에서 플래그를 끈 페이지의 기본 동작도 확인한다. 제품 통합 전 기능 이름과 호출 흐름을 최신 초안으로 재확인하고, WebMCP 호출의 인증·tenant 권한은 서버에서 별도 검증한다.

## T20 제품 통합 결과

확인일: 2026-10-03 (Asia/Seoul)

- 공식 초안 [WebMCP](https://webmachinelearning.github.io/webmcp/)의 최신 발행본(2026-10-02)을 재확인했다. 실제 API는 `document.modelContext.registerTool(tool, options)`이며, `getTools()`는 문서 및 하위 문서에 노출된 도구 검색용이고 브라우저 agent는 별도 내부 메커니즘으로 목록을 얻는다. `executeTool(tool, inputObject)`는 초안상 페이지 내 호출 API다. 등록 옵션의 `signal`을 abort해 해제한다.
- 프런트는 로그인 세션이 있을 때 `document.modelContext.registerTool` feature detection 뒤에만 `search_requests`, `get_request`, `get_trace` 세 읽기 도구를 등록한다. 입력을 실행 핸들러에서도 검증하며, 기존 API 클라이언트의 세션 쿠키와 서버 권한 검사를 이용한다. 요청 목록 `query`는 API 미지원이므로 권한 적용된 목록의 ID/상태에 한정해 클라이언트 필터한다. 상세는 요청 상태와 판단 요약만, Trace는 단계 ID·종류·상태만 반환한다.
- 로그아웃에서 발생하는 `auth:unauthorized` 이벤트는 등록에 사용한 AbortSignal을 중단해 세 도구를 해제한다. WebMCP 미지원 시 등록 전에 반환하며 일반 앱 초기화는 계속된다.
- Vitest `frontend/src/webmcp/index.test.ts`: 3개 통과. feature 부재 시 0개 등록, 입력 검사/API 404 도구 오류 변환, 요약 결과의 원문 제외를 확인했다. `cd frontend && npm run typecheck`: 통과.
- Chrome 154.0.8037.97에서 `probes/webmcp/run_probe.sh enabled`를 실행했으나, Chrome headless 프로세스가 30초 이상 종료되지 않아 실행을 중단했다. Inspector/DevTools agent 호출 주체를 사용할 수 없어 실제 agent 호출 결과도 없다. 이번 probe로 등록·발견·제품 호출 성공을 주장하지 않는다.
- **G10 차단**: 구현은 끝났으나 게이트 통과 증거가 없다. 실제 필요한 증거는 WebMCP 플래그/Origin Trial이 활성화된 Chrome에서 제품 세 도구의 안정된 등록과 `getTools()` 발견, 로그인 세션의 도구 1회 실제 agent 호출 결과, 권한 밖 ID의 서버 404 도구 오류, 기능 비활성 환경에서 앱 정상 동작이다. 현재 도구 접근 테스트는 unit 수준이며 실제 브라우저 agent 호출자 연결이 미확보다.
