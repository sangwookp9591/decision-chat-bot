# T21 인수 시험 증거

- 최종 실행: `20261003T104827Z/` — `gate-evidence.md`(G01–G11 판정), `pytest.log`·`junit.xml`(35/35), `ui.log`·`ui-results.json`(10/10), `records/records.jsonl`(비민감 ID·집계), `ui/`(스크린샷·`ui-evidence.json`), `logs/`(API·worker·수집기·watchdog).
- 선행 실행 `20261003T103628Z/`, `20261003T104217Z/`: Live Jev 인용 가변성으로 S5 단정이 실패한 기록(각 1건 실패). 삭제하지 않고 남긴다.
- 재현: 저장소 루트에서 `make test-acceptance`.
