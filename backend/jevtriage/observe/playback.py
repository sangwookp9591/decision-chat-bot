"""Read-only saved execution playback."""

from jevtriage.db.tx import read_tx
from jevtriage.domain.serialize import json_value


async def get_playback(tenant_id: str, run_id: str):
    async def op(tx):
        result = await tx.run(
            "MATCH (r:Run {tenant_id:$tenant_id,id:$run_id}) "
            "OPTIONAL MATCH (r)-[:HAS_STEP]->(s:RunStep {tenant_id:$tenant_id}) "
            "OPTIONAL MATCH (v:Review {tenant_id:$tenant_id,request_id:r.request_id,run_id:r.id}) "
            "OPTIONAL MATCH (d:ReviewDecision {tenant_id:$tenant_id,review_id:v.id}) "
            "RETURN r,collect(DISTINCT s) AS steps,collect(DISTINCT v) AS reviews,collect(DISTINCT d) AS decisions",
            tenant_id=tenant_id, run_id=run_id,
        )
        row = await result.single()
        if not row: return None
        events=[]
        for s in row["steps"]:
            if not s: continue
            events.append({"type":"step_started","at":s.get("started_at"),"step_id":s["id"],"status":s.get("status")})
            if s.get("ended_at"):
                events.append({"type":"step_ended","at":s["ended_at"],"step_id":s["id"],"status":s.get("status"),"duration_ms":s.get("duration_ms")})
        decisions={d.get("review_id"):dict(d) for d in row["decisions"] if d}
        reviews=[]
        for v in row["reviews"]:
            if not v: continue
            d=decisions.get(v["id"]); ended=d.get("created_at") if d else None
            waiting=None
            if ended and v.get("created_at"):
                waiting=max(0,int((ended.to_native()-v["created_at"].to_native()).total_seconds()*1000))
            events.append({"type":"human_wait_started","at":v.get("created_at"),"review_id":v["id"]})
            if ended: events.append({"type":"human_wait_ended","at":ended,"review_id":v["id"],"duration_ms":waiting})
            reviews.append({"review_id":v["id"],"status":v.get("status"),"decision":d,"waiting_ms":waiting})
        events.sort(key=lambda e:(str(e.get("at") or ""), e["type"],e.get("step_id",e.get("review_id",""))))
        return {"request_id":row["r"].get("request_id"),"run_id":run_id,"config_version":row["r"].get("config_version"),"live":row["r"].get("status") in {"pending","running"},"events":events,"reviews":reviews,"final_result":row["r"].get("status")}
    return json_value(await read_tx(tenant_id,op))
