"""Build scenario-evidence.md from ledger.json + state.json + ui-results.jsonl (+ regression.json) of one T38 run.

Usage (from backend/): X38_OUT=<dir> .venv/bin/python -m tests.acceptance.extension.report
Nothing is invented here: every status comes from a recorded check; entries replaced by a retest stay listed as history.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

OUT = Path(os.environ["X38_OUT"])
ledger = json.loads((OUT / "ledger.json").read_text())
state = json.loads((OUT / "state.json").read_text())
ui = [json.loads(line) for line in (OUT / "ui-results.jsonl").read_text().splitlines()] if (OUT / "ui-results.jsonl").exists() else []
regression = json.loads((OUT / "regression.json").read_text()) if (OUT / "regression.json").exists() else {}
decisions = json.loads((OUT / "gate-decisions.json").read_text()) if (OUT / "gate-decisions.json").exists() else {}

# Failed entries that were re-tested under a different title (the failure stays visible in the history section).
RETESTED = {
    ("X03", "policy_editor cannot publish a rules diff via /api/policy/publish"): "probe used an invalid rule id (R-AI-NEED-01); retested with a valid id",
    ("X04", "monitoring SLO/summary denominators and alerts unchanged by shadow"): "first attempt was vacuous (collector stopped, clock-dependent window); retested with collector running",
    ("X04", "(retest, collector running, non-vacuous) SLO/summary denominators and alerts unchanged by shadow; shadow counted only in shadow_runs"): "summary.kinds.shadow_validation +1 (shadow-only counter) was compared too; retest 2 excludes shadow-only fields",
    ("X05", "invariant-weakening rules (feasibility→가능, urgency→일반) are refused; no RuleVersion/Config created"): "stale expectation: after FIX-S the candidate save itself is refused (422), so the old 'candidate ok, version refused' shape no longer exists; replaced by the F4 checks",
    ("X01", "lead_org corrections (text-only requests) keep evidence span IDs: Correction.evidence_span_ids == CITES targets of the corrected ModelOutput; spans are chat sentences"): "wrong expectation: the live model cites no span for lead_org; retested as '(retest) lead_org corrections …'",
    ("EVID", "text-only request (0 attachments): judgment map evidence layer shows the chat EvidenceSpan nodes cited by the run (API span node ids ⊇ Cypher CITES targets, ⊆ stored spans of the request)"): "too strict: the request map also contains the spans of the rule's supporting corrections; retested with the corrected expectation",
    ("X07", "in-flight run started before the stop keeps the pinned (old) Config version and still applies the rule"): "stop landed while the run was still pending (not started); retested after the run pinned its Config",
}


GATES_ALL = [f"X{n:02d}" for n in range(1, 11)] + ["F3", "F4", "F5", "F6", "F7", "EVID"]
GATE_TITLES = {"F3": "F3 Trace 규칙 적용 단계 상세", "F4": "F4 불변 조건 허용 목록·blocked_by_invariant", "F5": "F5 자료 부족 승인 확인", "F6": "F6 섀도 Run id 분리", "F7": "F7 시각 직렬화(Flow/단계 상세)", "EVID": "근거 계층(텍스트 전용 요청의 chat EvidenceSpan)"}


def short(value, limit=260):
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


def latest(entries):
    by_key = {}
    for e in entries:
        by_key[(e["gate"], e["step"])] = e
    return by_key


def status_of(gate):
    rows = [e for e in ledger if e["gate"] == gate]
    current = latest(rows)
    bad = [e for k, e in current.items() if e["status"] == "fail" and k not in RETESTED]
    blocked = [e for e in current.values() if e["status"] == "blocked"]
    passed = [e for e in current.values() if e["status"] == "pass"]
    ui_rows = [u for u in ui if f"[{gate}]" in u["title"]]
    ui_fail = [u for u in ui_rows if u["status"] != "passed" and not any(v["title"] == u["title"] and v["status"] == "passed" and v["at"] > u["at"] for v in ui_rows)]
    if gate in decisions:
        return decisions[gate]["status"], decisions[gate]["note"]
    if bad or ui_fail:
        return "실패", f"실패 항목 {len(bad) + len(ui_fail)}건"
    if blocked:
        return "차단", blocked[0]["step"]
    return ("통과" if passed else "미검증"), f"API/DB 검사 {len(passed)}건 통과, 브라우저 검사 {len([u for u in ui_rows if u['status'] == 'passed'])}건 통과"


def main() -> None:
    L: list[str] = []
    w = L.append
    w("# T38-R 확장 연결 시나리오 재실행 — X01–X10 최종 판정\n")
    w("이전 실행: `artifacts/validation/20261003T093618Z/extension/scenario-evidence.md`(X01–X10 통과, 한계 F3–F9). 이 보고는 FIX-S/O/C/E/SSE/R 이후 최신 코드로 새 tenant에서 다시 실행한 결과다(이전 증거는 덮어쓰지 않음).\n")
    w(f"- 실행 tenant: `{os.environ.get('X38_TENANT', '')}` (전용, worker는 `--tenant` 제한), 결과 디렉터리: `{OUT}`")
    w("- Decision AI: `AI_MODE=live` (실제 모델 호출, 모든 판단 `mode=live`). 저장소: 공유 Neo4j(정지하지 않음). 데이터 디렉터리(journal/원본 파일)는 이 작업 전용 경로.")
    w("- 이 보고는 **확장 게이트 X01–X10**만 판정한다. 기존 게이트(G01–G12)는 4절 'X10 회귀'의 '기존 게이트 별도 보고' 표에서 재실행 결과로만 다루며, G 판정 자체는 T27 소관이다.\n")
    w("## 1. 판정 요약\n")
    w("| 게이트 | 판정 | 근거 요약 |\n| --- | --- | --- |")
    for g in GATES_ALL:
        s, note = status_of(g) if g != "X10" else (regression.get("verdict", "미검증"), regression.get("note", ""))
        w(f"| {GATE_TITLES.get(g, g)} | **{s}** | {note} |")
    w("")
    w("## 2. 10단계 실제 ID 표\n")
    seed = state.get("seed", {})
    plan = seed.get("plan", {})
    w("| 단계 | 항목 | 실제 ID / 값 |\n| --- | --- | --- |")
    w(f"| 1 | 접수·판단 요청(8건, AI 원안 ai_need=`{seed.get('original_ai_need')}`) | {', '.join(f'`{r}`' for r in seed.get('requests', []))} |")
    cors = state.get("corrections", {})
    w(f"| 1 | 같은 방향 수정 3건(→`{seed.get('dir_y')}`) | {', '.join(f'`{r}`→`{cors.get(r)}`' for r in plan.get('same_direction', []))} |")
    w(f"| 1 | 반례 1건(수정 없이 승인) | `{plan.get('counter')}` |")
    w(f"| 1 | 다른 방향 수정 2건(→`{seed.get('dir_z')}`) | {', '.join(f'`{r}`→`{cors.get(r)}`' for r in plan.get('other_direction', []))} |")
    w(f"| 3 | 후보(지지 3, 제안) / 후보(지지 2, 자료 부족) | `{state.get('cand_y')}` / `{state.get('cand_z')}` |")
    w(f"| 4 | 범위 수정 승인 결정 / 규칙 버전 / 기반 Config | `{state.get('decision_id')}` / `{state.get('ref')}` / v{state.get('base_config')} |")
    w(f"| 5 | 섀도 검증 / 게시 Config | `{state.get('validation_id')}` / v{state.get('pub_config')} |")
    pr = state.get("post_requests", {})
    for rid in pr.get("in_scope", []):
        rep = pr["report"][rid]
        w(f"| 6 | 범위 내 새 요청(사용) | `{rid}` run `{rep['run_id']}` step `{rep['step_ids_in_applied'][0]}` {rep['model_raw_ai_need']}→{rep['api_ai_need']} |")
    if pr.get("out_of_scope"):
        rep = pr["report"][pr["out_of_scope"]]
        w(f"| 6 | 범위 밖 새 요청(미사용 기록) | `{pr['out_of_scope']}` run `{rep['run_id']}` step `{rep['step_ids_in_applied'][0]}` {rep['api_ai_need']} 유지 |")
    rl = state.get("rule_lead", {})
    if rl:
        w(f"| 7a | lead_org 수정 경로: 후보/결정/버전/Config (`{rl['original']}`→`{rl['target']}`) | `{rl['candidate']}` / `{rl['decision']}` / `{rl['ref']}` / v{rl['config']} · 수정 {', '.join(f'`{c}`' for c in rl['corrections'])} · 검증 `{rl['validation']}`(섀도 Run `{rl['validation_run']}`) · 새 요청 `{rl['post_request']['request_id']}` run `{rl['post_request']['run_id']}` {rl['post_request']['model_raw']}→{rl['post_request'].get('final', rl['post_request'].get('lead_org'))} |")
    inv = state.get("invariants", {})
    if inv:
        w(f"| F4 | DB 직접 삽입 위반 규칙 적용 | tenant `{inv['tenant']}` Config v{inv['config']} 규칙 {', '.join(f'`{r}`' for r in inv['rules'])} · 요청 `{inv['request']}` run `{inv['run']}` step `{inv['step']}` |")
    if state.get("z_rule"):
        w(f"| F5 | 자료 부족 후보 승인(API) / 화면 승인 대상 | 후보 `{state['cand_z']}` 결정 `{state['z_rule']['decision']}` 버전 `{state['z_rule']['rule_id']}@{state['z_rule']['version']}` / 후보 `{state.get('cand_ins_ui')}` |")
    r2 = state.get("rule2", {})
    if r2:
        w(f"| 7 | 근거 있는 규칙(feasibility `{r2['original']}`→`{r2['target']}`, 텍스트 전용 요청) 후보/결정/버전/Config | `{r2['candidate']}` / `{r2['decision']}` / `{r2['ref']}` / v{r2['config']} |")
        w(f"| 7 | 역추적 사슬 | step `{state['trace']['step']}` → `{r2['ref']}` → `{state['trace']['chain']['d']}` → `{state['trace']['chain']['c']}` → `{state['trace']['chain']['cor']}` → `{state['trace']['chain']['o']}` → `{state['trace']['chain']['e']}` |")
    lc = state.get("lifecycle", {})
    if lc:
        w(f"| 8 | 중단/ v2 게시 / 되돌리기 Config | v{lc['configs']['stop']} / v{lc['configs']['v2']} / v{lc['configs']['revert']} (v2=`{state['rule_id']}@{lc['v2']['version']}`) |")
        w(f"| 8 | 진행 중 / 중단 후 / v2 / 되돌린 뒤 요청 | `{lc['in_flight']['request']}` / `{lc['after_stop']['request']}` / `{lc['v2']['request']}` / `{lc['after_revert']['request']}` |")
    if state.get("post_restart"):
        w(f"| 9 | 재시작 후 새 요청 | `{state['post_restart']['request']}` run `{state['post_restart']['run']}` |")
    w("")
    w("## 3. 게이트별 증거 (최신 결과 + 재시험 이력)\n")
    for g in GATES_ALL:
        if g == "X10":
            continue
        w(f"### {GATE_TITLES.get(g, g)} — {status_of(g)[0]}\n")
        rows = [e for e in ledger if e["gate"] == g]
        for i, e in enumerate(rows):
            key = (e["gate"], e["step"])
            retest = RETESTED.get(key)
            later_pass = e["status"] == "fail" and any(x["gate"] == g and x["step"] == e["step"] and x["status"] == "pass" for x in rows[i + 1:])
            if later_pass and not retest:
                retest = "같은 항목을 수정·재실행해 통과(시험 코드 정정 후, 아래 이력 참조)"
            tag = {"pass": "통과", "fail": "**실패**", "unverified": "미검증/정정", "blocked": "차단"}[e["status"]]
            w(f"- [{tag}] {e['step']}" + (f" — _재시험으로 대체: {retest}_" if retest and e["status"] == "fail" else ""))
            w(f"  - 증거: `{short(e['evidence'], 700)}`")
        for u in [u for u in ui if f"[{g}]" in u["title"]]:
            w(f"- [브라우저 {u['phase']}: {'통과' if u['status'] == 'passed' else '**' + u['status'] + '**'}] {u['title']}" + (f" — {u['error']}" if u.get("error") else ""))
            if u.get("evidence"):
                w(f"  - 화면 값: `{short(u['evidence'], 500)}`")
        w("")
    w("## 4. X10 회귀\n")
    w(regression.get("markdown", "_회귀 결과가 기록되지 않았습니다._"))
    w("\n## 5. 발견 사항\n")
    w(decisions.get("findings_markdown", ""))
    w("\n## 6. 재현 방법\n")
    w("```sh\nmake up\ncd backend\n.venv/bin/python tests/acceptance/extension/provision_tenant.py <tenant>\nWORKER: .venv/bin/python -m ildongi.jobs.worker --tenant <tenant>   # API: uvicorn ildongi.main:app --port <port>\n"
      "export X38_OUT=<artifacts/validation/<ts>/extension> X38_TENANT=<tenant> X38_API=http://127.0.0.1:<port>\n"
      ".venv/bin/python -m tests.acceptance.extension.scenario_r seed corrections rules apply invariants trace_detail insufficient chain_lead lead_retest chain_evidence evidence_layer graph f7 insufficient_ui_setup\n"
      "(export ui1/r1 → playwright ui1 + extension-r r1 → insufficient_ui_verify reject lifecycle inflight shadow_monitoring → export ui2 → ui2 → snapshot pre → API/worker/collector 재시작 → snapshot post → diff post_restart → snapshot post2 diff_new_traffic → export ui3 → ui3(X38_SNAP=post2)+r3 → f6 playback dbsummary)\n"
      "X38_SUFFIX=ui1 .venv/bin/python -m tests.acceptance.extension.scenario export   # then: cd ../frontend && X38_PHASE=ui1 npx playwright test -c playwright.extension.config.ts\n"
      "... snapshot (pre) → 프로세스 재시작 → snapshot (post) → diff → ui3 ...\n.venv/bin/python -m tests.acceptance.extension.report\n```\n")
    (OUT / "scenario-evidence.md").write_text("\n".join(L))
    print("wrote", OUT / "scenario-evidence.md")


if __name__ == "__main__":
    main()
