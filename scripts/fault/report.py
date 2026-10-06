#!/usr/bin/env python3
"""Create a Korean status report from an executed fault pytest run."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

SCENARIOS = {
    "Decision AI 장애": ["test_ai_faults"],
    "파서·Neo4j 장애": ["test_parser_and_db_outage"],
    "worker 인계·재시작": ["test_worker_handoff_and_kill_recovery"],
    "API 재시작·SSE": ["test_api_restart_and_sse_recovery"],
    "정책 도중 변경": ["test_policy_version_pinned_and_rollback"],
    "동시 승인": ["test_parallel_review_and_idempotent_retry"],
    "관측 장애": ["test_observation_outages_and_reconciliation"],
    "보완·120초 뒤 회복": ["test_information_wait_and_late_recovery"],
}


def main(folder: Path) -> None:
    cases = {}
    junit = folder / "junit.xml"
    if junit.exists():
        for node in ET.parse(junit).iter("testcase"):
            cases[node.get("name", "")] = (
                "실패" if node.find("failure") is not None or node.find("error") is not None
                else "미검증" if node.find("skipped") is not None else "통과")
    observations = []
    path = folder / "scenarios.jsonl"
    if path.exists():
        observations = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    lines = ["# T22 장애 시험 결과", "", f"실행: {datetime.now(UTC).isoformat()} UTC",
             f"증거: `{folder}`", "", "| 시나리오 | 판정 | 증거 |", "| --- | --- | --- |"]
    for label, prefixes in SCENARIOS.items():
        selected = [state for name, state in cases.items()
                    if any(name.startswith(prefix) for prefix in prefixes)]
        status = ("미검증" if not selected else "실패" if "실패" in selected else
                  "미검증" if "미검증" in selected else "통과")
        lines.append(f"| {label} | {status} | `pytest.log`, `junit.xml`, `scenarios.jsonl` |")
    lines += ["", "## 기록된 실행 값", "", "```json"]
    lines += [json.dumps(row, ensure_ascii=False) for row in observations]
    lines += ["```", ""]
    sse_samples = [row["recovery_ms"] for row in observations
                   if row.get("scenario") == "api_restart_sse" and "recovery_ms" in row]
    if sse_samples:
        observed_p95 = sorted(sse_samples)[(95 * len(sse_samples) + 99) // 100 - 1]
        lines.append(f"SSE 재연결 p95: {observed_p95}ms / 기준 5000ms, 표본 {len(sse_samples)}건. "
                     "단일 로컬 표본은 운영 성능 달성 판정으로 사용하지 않는다.")
    else:
        lines.append("SSE 재연결 p95: 미검증.")
    lines.append("Decision AI 장애 주입 결과는 AI_MODE=mock이며 실연동 품질 게이트를 대체하지 않는다.")
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
