# 의존성 감사

## 2026-10-05

실행 위치는 `frontend/`이며 `npm audit --json`을 lockfile 포함 전체 의존성에 실행했다. 311개 패키지에서 취약점 7건(중간 5, 높음 1, 치명 1)이 나왔다. 경고는 Vitest 2.x와 하위 Vite/esbuild 경로의 개발 의존성 및 React Router 6.28 계열 2건이다. npm이 제안한 Vitest 5와 React Router 7은 메이저 업그레이드이며 이 작업에서 호환성 검증을 하지 않아 적용하지 않았다.

| 패키지 | 범위 | 판정 |
| --- | --- | --- |
| `react-router`, `react-router-dom` | CVE-2025-68470, GHSA-337j-9hxr-rhxg; `<7.18.0` | 중간 2건. 호환 수정버전이 현재 6.x 범위에 없고 제안은 7.18.4라 보류 |
| `vitest`, `@vitest/mocker`, `vite`, `vite-node`, `esbuild` | 개발 도구 체인; audit fix는 Vitest 5.0.3 제안 | 중간 3, 높음 1, 치명 1. 메이저 변경 및 런타임 미검증으로 보류 |

실행 명령: `cd frontend && npm audit --json` (exit 1, 7 findings; 0 low). `package.json`과 `package-lock.json`은 변경하지 않았다.

Python은 `backend/.venv`에 개발 도구 `pip-audit 2.10.1`을 설치해 `cd backend && .venv/bin/python -m pip_audit -r requirements.lock`으로 실행했다. `pytest 8.4.2`에서 `PYSEC-2026-1845` 2개 advisory 항목이 보고됐고 수정 제안은 9.0.3이다. requirements.lock은 변경하지 않았다. 별도 취약점 해소 작업에서 pytest 9 호환성 검증 후 lock을 갱신한다.

## CORS 및 브라우저 경계

현재 FastAPI 앱에는 `CORSMiddleware`가 없다. 브라우저 구성은 Vite의 `/api` same-origin proxy를 사용하므로 개발 UI와 API가 같은 origin으로 보인다. 배포 환경에서는 reverse proxy가 UI/API를 same-origin으로 제공해야 한다. 별도 origin 구성이 필요해지면 운영 UI origin을 명시적으로 allowlist하고 credentials 사용 시 wildcard를 금지하며, `OPTIONS`와 인증 쿠키/CSRF 헤더를 검증하는 경계 시험과 함께 정책을 코드화한다. 현재 API는 임의 origin에 CORS 접근을 허용하지 않는다.
