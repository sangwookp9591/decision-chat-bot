# 일동이 ChatGPT 개발 플러그인

2026-10-07 기준. 공식 Python MCP SDK `mcp==1.30.0`의 `/mcp`는 **무상태 JSON 응답**으로 실행합니다. 기본 연결은 Cloudflare Quick Tunnel이며 계정·API 키 없이 시험할 수 있습니다. [Cloudflare 공식 Quick Tunnel 안내](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)

## ChatGPT 새 플러그인 화면 입력값

| 항목 | 입력값 |
| --- | --- |
| 이름 | **일동이** |
| 설명 | **업무 요청의 AI 필요성·실현 가능성·긴급성·담당 조직 판단, 검토 대기 및 배정 업무를 조회합니다.** |
| 연결 | **서버 URL** 탭 |
| 서버 URL | `https://<무작위>.trycloudflare.com/mcp` — `.data/mcp-tunnel-url.txt`의 전체 값 |
| 인증 | **인증 없음** — 개발 시험용 |
| 아이콘 | [docs/mcp/icon.png](icon.png), 96×96 PNG |

도구 목록에 읽기 도구 4개가 표시되는지 확인하고 새 대화에서 일동이를 선택합니다. ChatGPT 화면 경로·명칭은 계정별로 다를 수 있으며 이 문서의 입력값은 요청된 화면 기준입니다. 실제 ChatGPT 도구 실행은 curl 전송 시험과 별도로 확인해야 합니다.

## 기본 실행·재연결·종료

기존 README의 Neo4j·개발 계정 준비를 사용합니다. 기존 컨테이너를 재사용하며 Redis를 기동하지 않습니다. 기존 `.env`를 덮어쓰지 않습니다.

```dotenv
MCP_AUTH_MODE=dev
MCP_DEV_USER=requester@t-alpha.dev
MCP_PORT=8787
MCP_ALLOW_SUBMIT=0
MCP_SSE_ENABLED=0
```

```sh
# cloudflared가 없을 때만 설치
brew install cloudflared
# 터미널 1: loopback MCP
make mcp
# 기존 로컬 runtime을 사용한다면: python3 .data/runtime.py restart mcp
# 터미널 2: 계속 실행해 둘 Quick Tunnel
bash scripts/mcp/quick_tunnel.sh
```

스크립트는 `cloudflared tunnel --url http://127.0.0.1:${MCP_PORT:-8787} --no-autoupdate`를 실행하며 URL에 `/mcp`를 붙여 화면과 `.data/mcp-tunnel-url.txt`에 출력합니다. 원본 Host는 `TUNNEL_HTTP_HOST_HEADER`로 loopback에 맞추므로 SDK의 Host 보호를 해제하지 않습니다. 터널 PID는 `.data/mcp-tunnel.pid`, 로그는 `.data/mcp-quick-tunnel.log`에 기록합니다. 스크립트의 `MCP_PORT`는 셸 환경변수이므로 포트를 변경했다면 MCP와 터널 양쪽에 동일하게 지정하세요. [공식 macOS 설치 방법](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)

Quick Tunnel은 **재시작마다 URL이 바뀝니다**. 서버·터널 기동 → 새 URL 파일 확인 → ChatGPT 기존 일동이 편집 → 서버 URL 교체·저장 → 새 대화에서 도구 재확인 순서로 연결합니다. 이전 URL을 재사용하지 않습니다.

**인증 없는 공개 노출입니다. URL을 아는 누구나 같은 개발 계정의 조회 권한을 사용하므로 개인 시험에만 사용하고 시험 직후 즉시 종료하세요.** 터널은 Ctrl-C 또는 `kill "$(cat .data/mcp-tunnel.pid)"`, MCP는 Ctrl-C 또는 `python3 .data/runtime.py stop mcp`로 종료합니다. 공유 API·워커·Neo4j는 종료하지 않습니다. 파일에 남은 URL/PID는 실행 상태를 보증하지 않습니다.

## 전송 확인

현재 URL을 설정하고 아래 두 요청을 실행합니다. `/mcp`는 `application/json`이며 세션 ID 재사용이 필요 없습니다.

```sh
MCP_URL=$(cat .data/mcp-tunnel-url.txt)
curl --fail-with-body --max-time 20 "$MCP_URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"local-check","version":"1"}}}'
curl --fail-with-body --max-time 20 "$MCP_URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-03-26' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
backend/.venv/bin/python scripts/mcp/check.py
(cd backend && .venv/bin/pytest -q tests/unit/test_mcp_server.py)
make lint
```

## 도구·제한·권한

| 도구 | 기본 노출 | 결과 |
| --- | --- | --- |
| `get_request_result(request_id)` | 읽기 | 진행·잠정/최종 분류·신뢰도·규칙·업무 초안 |
| `list_my_requests(limit)` | 읽기 | 본인/공유 조직의 권한 있는 요청 |
| `list_review_queue(limit)` | 읽기 | 검토 권한 조직의 대기 목록 |
| `list_tasks(limit)` | 읽기 | 조직·역할별 조회 가능한 배정 업무 |
| `submit_request(text)` | **기본 미등록**, `MCP_ALLOW_SUBMIT=1` 후 재시작 시 등록 | 새 요청 접수; 재호출은 새 요청 생성 |

두 전송은 같은 도구 등록을 공유합니다. 목록 limit은 1~10(기본 10), 본문은 16KiB, 도구 결과는 512KiB 상한입니다. submit 텍스트 스키마는 1~20,000자이며 HTTP 본문 제한도 동시에 적용됩니다. 결과가 너무 크면 데이터를 보내지 않고 MCP 도구 오류로 거부합니다. 요청 횟수·동시는 두 경로를 합쳐 프로세스 전체 분당 60회·동시 4회이며 횟수·동시·본문 초과 시 HTTP 429와 `Retry-After: 60`을 반환합니다. 이 예산은 로컬 단일 프로세스용이고 다중 프로세스 운영은 gateway 제한이 필요합니다.

각 도구는 한국어 설명, 입력/출력 스키마, text 요약과 structuredContent를 제공합니다. `judgment=null`은 최종 판단 전이며 잠정 값을 최종으로 해석하지 않습니다. 매 호출마다 개발 계정의 활성 membership·tenant·역할·원문 권한을 확인하고 웹 API의 scope·원문 소유자 예외·redact_source를 재사용합니다. 오류에 원문·비밀값을 반사하지 않습니다. `dev` 미설정, 다른 인증 모드, 비-loopback 바인딩은 기동 거부합니다. 미사용 OAuth discovery는 404입니다.

쓰기 시험은 개인 로컬 환경에서만 `MCP_ALLOW_SUBMIT=1`로 재시작하고 AI_MODE를 확인한 뒤 `scripts/mcp/check.py --submit`으로 실행합니다. 자동 재시도는 중복 접수를 만들 수 있으므로 반환된 ID를 먼저 조회합니다. 시험 후 쓰기 플래그를 다시 끄고 재시작합니다. 운영 사용자별 인증은 아직 구현하지 않았으며 OAuth/SIWC와 tenant 연결이 별도 과제입니다.

## 선택적 SSE 계획

`MCP_SSE_ENABLED=0`이 기본이며 `/mcp/stream`은 404입니다. `MCP_SSE_ENABLED=1`로 MCP를 재시작하면 같은 도구의 Streamable HTTP SSE 응답(`text/event-stream`) 경로가 추가됩니다. `/mcp`의 JSON 모드는 그대로 유지합니다. 현재 조회는 단일 결과라 JSON이면 충분합니다.

SSE를 선택하는 기준은 작업 중 진행률 알림, 서버 주도 메시지, 장시간 작업의 부분 결과 스트리밍입니다. 현재 선택적 경로는 stateless로 요청 내 SSE를 지원하며 독립적인 서버 주도 알림·재연결 세션·진행률 생산 기능은 아직 구현하지 않았습니다. 해당 기능이 실제 필요하면 세션 수명·재연결·권한 재검증을 함께 설계해야 합니다.

**Cloudflare Quick Tunnel은 SSE를 지원하지 않습니다.** SSE 공개 시험에는 **Cloudflare Named Tunnel 또는 ngrok**가 필요합니다. Quick Tunnel에 `/mcp/stream`을 연결하지 않습니다. 로컬 확인은 위 initialize curl의 URL만 `http://127.0.0.1:8787/mcp/stream`으로 바꾸고 응답 헤더를 `-i`로 확인합니다. 확인 후 플래그를 다시 0으로 재시작하세요. [공식 SSE 제한](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/#limitations)

## 대안: OpenAI tunnel-client (기본 경로 아님)

1. [Platform 터널 설정](https://platform.openai.com/settings/organization/tunnels)에서 사용할 Platform 조직을 선택합니다. 생성·편집에는 조직 권한 **Tunnels Read + Manage**, 실행·선택에는 **Read + Use**가 필요합니다.
2. 새 터널을 만들고 `tunnel_id`를 확인합니다. 개인 시험은 해당 계정의 개인 Platform 조직을 사용하고, ChatGPT가 사용하는 workspace도 터널에 연결합니다. 조직에만 연결된 터널은 다른 ChatGPT workspace에서 자동으로 보이지 않습니다.
3. Platform의 **Runtime API keys**에서 별도의 런타임 키를 만듭니다. **Restricted → Tunnels Read + Use**로 제한합니다. 관리자 키 또는 모든 권한 키를 장기 실행에 사용하지 않습니다.
4. 루트 `.env`에 `CONTROL_PLANE_TUNNEL_ID`와 `CONTROL_PLANE_API_KEY`를 저장합니다. 키는 이 문서·채팅·명령줄 인자·로그·Git에 기록하지 않습니다. 발급된 실제 값은 이 저장소에 포함하지 않습니다.

권한이 없으면 조직 owner/RBAC 관리자가 부여해야 합니다. 새 권한 반영에 시간이 걸릴 수 있습니다. [공식 end-user guide](https://github.com/openai/tunnel-client/blob/main/docs/end-user-guide.md), [온보딩](https://github.com/openai/tunnel-client/blob/main/docs/onboarding.md)

### 대안 실행 순서

저장소 루트에서 실행합니다. 기존 README의 로컬 Neo4j·계정 시드가 준비되어 있어야 합니다. 기존 컨테이너와 워커를 재사용하고 Redis는 필요하지 않습니다. `AI_MODE`는 원래 `.env` 값을 사용합니다. 현재 개발 시험은 `mock`으로 확인했으며, 아래 smoke의 쓰기는 반드시 mock 여부를 확인한 뒤 실행합니다.

```dotenv
# 루트 .env에 추가: dev 미설정이면 기동 거부
MCP_AUTH_MODE=dev
MCP_DEV_USER=requester@t-alpha.dev
MCP_PORT=8787
# 실제 값은 Platform에서 발급받아 로컬 .env에만 저장
CONTROL_PLANE_API_KEY=
CONTROL_PLANE_TUNNEL_ID=
```

```sh
# 백엔드 의존성 설치(기존 가상환경)
backend/.venv/bin/python -m pip install -r backend/requirements.lock

# 터미널 1: MCP 서버 (http://127.0.0.1:8787/mcp)
make mcp

# 터미널 2: 최종 판단을 생성할 기존 워커가 없다면 실행
make worker

# 공식 macOS arm64 최신 release ZIP 설치 + GitHub SHA256 검증
bash scripts/mcp/install.sh

# 로컬 MCP → 터널 프로필 생성 → 진단 → 계속 실행
backend/.venv/bin/python scripts/mcp/tunnel.py init
backend/.venv/bin/python scripts/mcp/tunnel.py doctor
backend/.venv/bin/python scripts/mcp/tunnel.py run
```

`init`은 공식 `sample_mcp_remote_no_auth`와 `--mcp-server-url http://127.0.0.1:8787/mcp`를 사용합니다. 프로필은 Git에서 제외된 `.data/mcp-tunnel/`, 바이너리는 `.data/bin/tunnel-client-release/`에 저장됩니다. 키는 프로필에 literal로 저장하지 않고 `env:CONTROL_PLANE_API_KEY` 참조를 사용합니다. 래퍼는 루트 `.env`를 셸 실행 없이 읽고, 키·ID가 비어 있으면 발급 안내와 함께 종료합니다. `MCP_PORT`를 바꾸면 새 프로필의 로컬 URL도 해당 포트로 설정됩니다.

macOS Gatekeeper가 직접 다운로드한 ZIP 바이너리를 차단할 수 있습니다. 우회하지 말고 공식 권장 설치인 `brew install openai/tools/tunnel-client`를 사용하세요. 래퍼는 공식 Homebrew 설치본을 우선 사용합니다. [공식 README 설치 안내](https://github.com/openai/tunnel-client#install-with-homebrew)

`run`을 계속 켜 둔 상태에서 ChatGPT 플러그인을 생성합니다. 기본 터널 관리 UI는 `http://127.0.0.1:8080/ui`, 상태 확인은 `/healthz`, `/readyz`입니다. `.data/runtime.py`를 사용하는 로컬 환경에는 `mcp` 서비스가 추가되어 있어 `python3 .data/runtime.py start mcp`도 사용할 수 있습니다. 종료는 각 터미널의 Ctrl-C 또는 `python3 .data/runtime.py stop mcp`입니다. [공식 설정 안내](https://github.com/openai/tunnel-client/blob/main/docs/configuration.md)

