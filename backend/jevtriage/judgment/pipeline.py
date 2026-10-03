from __future__ import annotations

from dataclasses import asdict

from .catalog import CATALOG_VERSION
from .decompose import decompose
from .eligibility import evaluate_auto_assign
from .evidence import link_evidence, select_units
from .questions import ORG_KEYS, QSET_VERSION, RISK_KEYS, questions

SCHEMA_VERSION = "judgment-v1"
MAX_EVIDENCE_UNITS = 12
MAX_EVIDENCE_CHARS = 2000
EVIDENCE_NOUL_THRESHOLD = 0.6
TEAM_INVOLVEMENT_THRESHOLD = 0.5
CATALOG_NOUL_THRESHOLD = 0.5

def run_judgment(input_units, chat_text, policy_snapshot, client, *, chat_context_text=None):
    units = select_units(
        input_units, chat_text,
        max_units=policy_snapshot.get("max_evidence_units", MAX_EVIDENCE_UNITS),
        max_chars=policy_snapshot.get("max_evidence_chars", MAX_EVIDENCE_CHARS),
    )
    state = {"units": [{"unit_id": unit_id, "text": text} for unit_id, text in units],
             "chat_text": chat_context_text if chat_context_text is not None else (chat_text or "")}
    result=client.ask(state,questions())
    answers=result.answers
    classifications={k:answers[k]["choice"] for k in ("ai_need","feasibility","urgency","lead_org")}
    evidence = (link_evidence(units, classifications, client,
                              policy_snapshot.get("evidence_noul_threshold", EVIDENCE_NOUL_THRESHOLD))
                if units else {key: [] for key in classifications})
    evidence_dict={k:[asdict(x) for x in v] for k,v in evidence.items()}
    risk_values={k:answers[k]["noul"] for k in RISK_KEYS}
    risk_clear_max=policy_snapshot.get("risk_clear_max",0.2)
    org_threshold=policy_snapshot.get("team_involvement_threshold", TEAM_INVOLVEMENT_THRESHOLD)
    signals={k:answers[k]["noul"] for k in ORG_KEYS}
    teams=[org for key,org in zip(ORG_KEYS,("AI팀","IT팀","현업")) if signals[key]>=org_threshold]
    tasks, decomposition=decompose(state,client,evidence_refs=policy_snapshot.get("task_evidence_refs"),threshold=policy_snapshot.get("catalog_noul_threshold",CATALOG_NOUL_THRESHOLD),risk_signals=risk_values,risk_clear_max=risk_clear_max,involved_orgs=teams)
    judgment={**classifications,"risk_confirmed":all(v<=risk_clear_max for v in risk_values.values()),"risks":{k:v>=0.5 for k,v in risk_values.items()},"risk_signals":risk_values,"teams":teams,"signals":signals,"review_confidence":answers["review_signal"].get("confidence",0),"draft_tasks":tasks}
    allowed,reasons=evaluate_auto_assign(judgment,policy_snapshot,{"input_confirmed":policy_snapshot.get("input_confirmed",False),"latest_run":True,"evidence_complete":bool(units),"already_assigned":policy_snapshot.get("already_assigned",False)})
    summary="\n".join(t for _,t in units[:3])
    return {"classifications":classifications,"teams":teams,"risk":{"confirmed":judgment["risk_confirmed"],"signals":risk_values,"clear_max":risk_clear_max},"raw_model_output":asdict(result),"evidence":evidence_dict,"summary":{"text":summary,"author":"code:extractive@1"},"draft_tasks":tasks,"review_reasons":reasons,"eligibility":{"allowed":allowed,"reasons":reasons},"versions":{"model":result.model,"qset":QSET_VERSION,"catalog":CATALOG_VERSION,"schema":SCHEMA_VERSION},"usage":{"input_tokens":result.usage["input_tokens"],"output_tokens":result.usage["output_tokens"],"latency_ms":result.latency_ms,"attempts":result.attempts,"mode":result.mode},"decomposition_output":asdict(decomposition)}
