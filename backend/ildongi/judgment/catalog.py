from __future__ import annotations

CATALOG_VERSION = "catalog-v2"
CATALOG = {
 "data_review": {"needed_when":"Whether the needed data exists, is accessible and of usable quality is not yet established.", "title":"데이터 확인", "method":"일반 기술", "lead_org":"IT팀", "collab_org":["현업"], "deliverable":"데이터 범위·품질 확인 결과", "predecessors":[]},
 "requirements": {"needed_when":"Acceptance criteria or scope of the request are not yet fixed by the business.", "title":"요구 기준 확정", "method":"사람", "lead_org":"현업", "collab_org":[], "deliverable":"승인된 기준과 수용 조건", "predecessors":["data_review"]},
 "ai_assessment": {"needed_when":"A learned model (prediction, classification, recommendation, generation) may be part of the solution and its suitability must be assessed.", "title":"예측·AI 모델 검토", "method":"AI", "lead_org":"AI팀", "collab_org":["현업","IT팀"], "deliverable":"모델 적합성·평가 계획", "predecessors":["data_review","requirements"]},
 "integration": {"needed_when":"Data must be moved or connected between systems.", "title":"데이터 연결·ETL", "method":"일반 기술", "lead_org":"IT팀", "collab_org":["현업"], "deliverable":"검증된 데이터 흐름", "predecessors":["data_review"]},
 "reporting": {"needed_when":"A screen, report or dashboard must be built.", "title":"화면·리포트 개발", "method":"일반 기술", "lead_org":"IT팀", "collab_org":["현업"], "deliverable":"검증된 화면 또는 리포트", "predecessors":["requirements","integration"]},
 "alerts": {"needed_when":"Notifications or alerts to people must be sent.", "title":"알림 연동", "method":"일반 기술", "lead_org":"IT팀", "collab_org":["현업"], "deliverable":"수신·오탐 기준을 갖춘 알림", "predecessors":["requirements","integration"]},
 "security": {"needed_when":"Access control or protection of sensitive data must be decided.", "title":"권한·보안 검토", "method":"사람", "lead_org":"IT팀", "collab_org":["현업"], "deliverable":"접근 통제·보안 확인", "predecessors":[]},
 "operations": {"needed_when":"Operating responsibility or business approval criteria must be fixed.", "title":"현업 승인·운영 기준 확정", "method":"사람", "lead_org":"현업", "collab_org":["IT팀"], "deliverable":"운영 책임·승인 기준", "predecessors":["requirements"]},
 "regulatory": {"needed_when":"Expert, regulatory or safety review is required to carry out the work.", "title":"규제·안전 검토", "method":"사람", "lead_org":"현업", "collab_org":["AI팀","IT팀"], "deliverable":"전문 검토와 승인 기록", "predecessors":[]},
}
