# 공식 자료와 확인 범위

확인일은 2026년 10월 2일이다. 아래는 기술 역할과 호환성 판단의 근거이며 API 접근·한국어 정확도·브라우저 동작·프로젝트 성능의 검증 결과는 아니다.

| 공식 자료 | 문서에 반영한 사실 |
| --- | --- |
| [TypeSafe AI 소개](https://docs.typesafe.ai/introduction) | Jev는 state와 typed questions에 대한 구조화된 판단 모델. Choice·Score의 confidence와 Noul의 확률은 다른 필드 |
| [TypeSafe AI](https://typesafe.ai/) | Jev가 확률과 신뢰 신호를 제공하고 애플리케이션이 자동 처리·검토 기준을 결정하는 역할 |
| [WebMCP 초안](https://webmachinelearning.github.io/webmcp/) | 2026년 9월 30일자 Draft Community Group Report. JavaScript 도구 노출 및 Document의 modelContext 정의. W3C 표준 아님 |

Jev의 속도·가격·정확도에 관한 홍보 수치는 이 프로젝트의 SLO 근거로 사용하지 않았다. Confidence를 업무 정답률로 취급하지 않는다. WebMCP 지원 여부와 호출 결과는 구현 환경에서 별도로 확인해야 한다.

FastAPI·Neo4j·SSE·Dynamic Config의 역할과 SLO 수치, 평가 목표, 입력 한도는 이 프로젝트를 위한 설계 요구 및 초기 제안이다. 특정 공급자가 보장하는 계약이나 공식 벤치마크가 아니다. 개발 에이전트는 구현 시점의 공식 문서·실제 의존성 버전·현재 프로젝트 규칙을 확인한다.

기존 대화의 첨부 이미지 원본은 확인하지 못했다. 화면 배치는 자유롭게 설계하고 실제 기록과의 연결을 검증한다.
