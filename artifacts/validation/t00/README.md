# T00 WebMCP probe evidence

확인일: 2026-10-03 (Asia/Seoul)

- `chrome-headless.html`: 로컬 Google Chrome headless에서 `--enable-features=WebMCP`와 `?selfTest=1`로 실행한 DOM 덤프. 실제 `document.modelContext` 등록·발견 및 페이지 컨텍스트의 `executeTool` 결과를 기록한다.
- `chrome-unsupported.html`: `--disable-features=WebMCP`에서 일반 페이지 내용과 미지원 안내가 표시된 DOM 덤프.
- 대응 stderr 파일에는 브라우저 진단 출력이 담겨 있으며 민감 정보는 포함하지 않는다.

`executeTool` 검증은 API를 통해 실제 등록 함수를 실행했음을 뜻하며, 별도 브라우저 에이전트가 호출했다는 증거는 아니다.
