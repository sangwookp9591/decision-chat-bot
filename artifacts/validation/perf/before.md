# PERF-1 before

Measured 2026-10-04 with one live Jev text request, tenant `perf1_67b1745cd2f04e928c485d4483476009`, run `run_799736278afb442b9b90fc9386221a38`. The script called `create_request`, then directly claimed and processed the Job with `Worker.process_job`; its reported `received_to_final_ms` was 2064 ms. RunStep times came from Neo4j and journal `worker_step` entries. There was no preliminary result or dedicated Jev classification/evidence/decomposition steps at baseline, so those call times cannot be separately attributed from this trace.

| Segment | Observed ms | Source/limit |
| --- | ---: | --- |
| request receive → Job created | 104 | script wall clock; includes DB writes |
| Run created → first RunStep started | 86 | Neo4j timestamps; worker dispatch/claim and setup |
| input preparation | 106 | RunStep |
| Jev classification + evidence calls + decomposition call | 1535 | combined `Jev 판단` RunStep |
| evidence validation | 6 | `근거 연결` RunStep; actual Jev calls were above |
| task validation | 8 | `업무 분해` RunStep; actual Jev call was above |
| rules | 6 | RunStep |
| eligibility | 6 | RunStep |
| final save | 184 | RunStep; includes persistence and events |
| Run created → judgment committed | 1986 | Neo4j timestamps |

This direct Job invocation does not measure empty-poll backoff. Production worker's default poll was 500 ms, doubling up to 8 s when idle; an arrival during that sleep could wait nearly 8 s.
