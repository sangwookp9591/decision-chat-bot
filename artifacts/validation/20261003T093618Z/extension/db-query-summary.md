# DB 질의 결과 요약 (T38)

tenant `t-x38-10031834` — 읽기 전용 Cypher, 값은 질의 실행 시점의 Neo4j 저장 결과.

## Correction (X01)

```cypher
MATCH (h:ReviewDecision {tenant_id:$tenant})-[:RECORDED]->(c:Correction) RETURN c.id,c.request_id,c.field,c.ai_value,c.corrected_value,c.corrected_by,c.run_id,c.config_version,size(c.evidence_span_ids) AS spans ORDER BY c.corrected_at
```

| c.id | c.request_id | c.field | c.ai_value | c.corrected_value | c.corrected_by | c.run_id | c.config_version | spans |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cor_82a6c2512ed649a8a3a48e82affb9e16 | req_a621234edfa84a52841609fb51a14bff | ai_need | "불필요" | "필요" | usr_t-x38-10031834_reviewer | run_dfbff2f5b2624464b2b403f64bbcb5f1 | 1 | 0 |
| cor_8145d2c72e3a4221b2e1564ec7ef3c58 | req_fb0bebc2ebe740c5902855dec3c4f7c5 | ai_need | "불필요" | "필요" | usr_t-x38-10031834_reviewer | run_ac3b864584c54ab7b8344b5238624a7f | 1 | 0 |
| cor_f00d744948d347d5a711f208ca08f2d6 | req_96562009f5aa47f199ab51abaeaed935 | ai_need | "불필요" | "필요" | usr_t-x38-10031834_reviewer | run_9c254957bedb4cb197f9b8ff7d4bb40c | 1 | 0 |
| cor_1a4435c4bbe4443bb4824d182bad736b | req_485f383761e34da2b7d1a4aa334d7e9e | ai_need | "불필요" | "혼합" | usr_t-x38-10031834_reviewer | run_1af75dc9f7434fc199444c19ecef99ec | 1 | 0 |
| cor_aacb1eb8f9ce4a36ac817912a0eb986d | req_3d34e25aee2f457da1abf7d5c9864ad7 | ai_need | "불필요" | "혼합" | usr_t-x38-10031834_reviewer | run_fdf5081bd1af4c93a6365bccc6f58ef6 | 1 | 0 |
| cor_b883b34442f34569bce57d37248bbd8f | req_245250b0119d49818ea62ce51724f863 | urgency | "긴급" | "판단 보류" | usr_t-x38-10031834_reviewer | run_723f5661b4f24f3da3c01bcaef1e3d03 | 2 | 1 |
| cor_3ed68e6a980e4aacba33b94e29d7f632 | req_957a2ff6918040bb9082bdb10a305065 | urgency | "긴급" | "판단 보류" | usr_t-x38-10031834_reviewer | run_fbf783b8a1534994a06bbb86384dc077 | 2 | 1 |
| cor_2053d3d03a044b54809204dcf9074c80 | req_f4e911dcb56547869d7263a1b928d09c | urgency | "긴급" | "판단 보류" | usr_t-x38-10031834_reviewer | run_23c51ff911b14e1ab9f461437e54965b | 2 | 1 |

## Candidate links (X02)

```cypher
MATCH (n:RuleCandidate {tenant_id:$tenant})-[r:SUPPORTED_BY]->(x) RETURN n.id,n.field,n.status,r.role,labels(x)[0] AS label,count(*) AS n ORDER BY n.id,r.role
```

| n.id | n.field | n.status | r.role | label | n |
| --- | --- | --- | --- | --- | --- |
| cand_861307de943efe054b1e407e | urgency | approved | counter | ReviewDecision | 1 |
| cand_861307de943efe054b1e407e | urgency | approved | support | Correction | 3 |
| cand_8fcc507094e6868374ddec5c | ai_need | approved | counter | ReviewDecision | 4 |
| cand_8fcc507094e6868374ddec5c | ai_need | approved | support | Correction | 3 |
| cand_e123faef72028b6d12635bef | ai_need | approved | counter | ReviewDecision | 5 |
| cand_e123faef72028b6d12635bef | ai_need | approved | support | Correction | 2 |

## Rule decisions (X03)

```cypher
MATCH (d:RuleDecision {tenant_id:$tenant})-[:DECIDES]->(c:RuleCandidate) RETURN d.id,c.id AS candidate,d.action,d.decided_by,d.confirmed_scope IS NOT NULL AS has_scope ORDER BY d.decided_at
```

| d.id | candidate | d.action | d.decided_by | has_scope |
| --- | --- | --- | --- | --- |
| rdec_b9981756b1e342278df9ee206130ae59 | cand_8fcc507094e6868374ddec5c | approve_with_scope_change | usr_t-x38-10031834_rule_admin | True |
| rdec_e08ce4b914814caeadf9f6dd817bb647 | cand_98a515be1dc7951ee1f85863 | approve | usr_t-x38-10031834_rule_admin | True |
| rdec_3dd585830eb5485e856c9e8868fb6a8a | cand_10385a10ef7bb9b9b9d496a3 | approve | usr_t-x38-10031834_rule_admin | True |
| rdec_ae5e2330872a441ea3fb562b5c28eaf8 | cand_861307de943efe054b1e407e | approve | usr_t-x38-10031834_rule_admin | True |
| rdec_553f62cfc5cb41b78344b4a8804258f1 | cand_e123faef72028b6d12635bef | approve | usr_t-x38-10031834_rule_admin | True |
| rdec_3c2a1de4e8de49f89f4a52e95ad4949d | cand_3251e2c1a26edd1fedc060d9 | reject | usr_t-x38-10031834_rule_admin | True |

## Rule versions and publication

```cypher
MATCH (r:RuleVersion {tenant_id:$tenant}) OPTIONAL MATCH (r)-[:PUBLISHED_IN]->(c:ConfigVersion) RETURN r.id,r.status,collect(c.version) AS configs ORDER BY r.id
```

| r.id | r.status | configs |
| --- | --- | --- |
| R-AI_NEED-01@1 | published | [8, 6, 2] |
| R-AI_NEED-01@2 | reverted | [5] |
| R-AI_NEED-02@1 | validating | [] |
| R-URGENCY-01@1 | published | [3] |

## Config versions

```cypher
MATCH (c:ConfigVersion {tenant_id:$tenant}) RETURN c.version,c.status,c.created_by,c.reason ORDER BY c.version
```

| c.version | c.status | c.created_by | c.reason |
| --- | --- | --- | --- |
| 1 | superseded | system:bootstrap | 보수적 초기 정책 |
| 2 | superseded | usr_t-x38-10031834_rule_admin | T38: 게시 |
| 3 | superseded | usr_t-x38-10031834_rule_admin | T38: 게시 |
| 4 | superseded | usr_t-x38-10031834_rule_admin | T38: 중단(진행 중 실행 시험) |
| 5 | superseded | usr_t-x38-10031834_rule_admin | T38: v2 게시 |
| 6 | superseded | usr_t-x38-10031834_rule_admin | T38: v1로 되돌리기 |
| 7 | superseded | usr_t-x38-10031834_rule_admin | T38: 진행 중 실행 시험 1 |
| 8 | active | usr_t-x38-10031834_rule_admin | T38: 시험 후 v1 복원 |

## ValidationRun (X04)

```cypher
MATCH (v:ValidationRun {tenant_id:$tenant}) RETURN v.id,v.rule_version,v.status,v.run_kind,v.sample_count,v.labeled_count,v.changed_count,v.side_effects ORDER BY v.created_at
```

| v.id | v.rule_version | v.status | v.run_kind | v.sample_count | v.labeled_count | v.changed_count | v.side_effects |
| --- | --- | --- | --- | --- | --- | --- | --- |
| val_14d2a9f8539a45e6bd94c3a88b748b64 | R-AI_NEED-01@1 | completed | shadow | 8 | 7 | 8 | 0 |
| val_ebc6fbf10d634862b9eae78b566dceb2 | R-URGENCY-01@1 | completed | shadow | 16 | 11 | 4 | 0 |
| val_bde46de0578d44028d74828ada71c5d1 | R-AI_NEED-01@2 | completed | shadow | 19 | 11 | 10 | 0 |
| val_2471af6ce59c452791b37f51e2b2465c | R-AI_NEED-02@1 | completed | shadow | 22 | 11 | 0 | 0 |
| val_150e1740ba754061b0e978f34c0a2c5a | R-AI_NEED-02@1 | completed | shadow | 22 | 11 | 0 | 0 |
| val_51fe535c35b74e9296890dd1cfb5f2eb | R-AI_NEED-02@1 | completed | shadow | 22 | 11 | 0 | 0 |

## RuleApplication (X05/X07)

```cypher
MATCH (s:RunStep {tenant_id:$tenant})-[a:APPLIED]->(rv:RuleVersion) RETURN rv.id AS rule,a.outcome,count(*) AS n ORDER BY rule,a.outcome
```

| rule | a.outcome | n |
| --- | --- | --- |
| R-AI_NEED-01@1 | out_of_scope | 6 |
| R-AI_NEED-01@1 | used | 6 |
| R-AI_NEED-01@2 | used | 1 |
| R-URGENCY-01@1 | out_of_scope | 6 |
| R-URGENCY-01@1 | used | 1 |

## Audit by action

```cypher
MATCH (a:Audit {tenant_id:$tenant}) WHERE a.action STARTS WITH 'rule.' RETURN a.action,count(*) AS n ORDER BY a.action
```

| a.action | n |
| --- | --- |
| rule.decision | 6 |
| rule.publish | 3 |
| rule.revert | 2 |
| rule.stop | 2 |
| rule.validated | 3 |
| rule.version_created | 4 |

## Events by kind (rule.*)

```cypher
MATCH (e:Event {tenant_id:$tenant}) WHERE e.kind STARTS WITH 'rule.' RETURN e.kind,count(*) AS n ORDER BY e.kind
```

| e.kind | n |
| --- | --- |
| rule.decision | 6 |
| rule.publish | 3 |
| rule.revert | 2 |
| rule.stop | 2 |
| rule.validated | 3 |
| rule.version_created | 4 |

## Graph relationships among learning nodes

```cypher
MATCH (a {tenant_id:$tenant})-[r]->(b {tenant_id:$tenant}) WHERE type(r) IN ['CITES','CORRECTS','RECORDED','SUPPORTED_BY','DECIDES','DERIVED_FROM','PUBLISHED_IN','VALIDATES','APPLIED','USED_OUTPUT'] RETURN type(r) AS type,count(*) AS n ORDER BY type
```

| type | n |
| --- | --- |
| APPLIED | 20 |
| CITES | 4 |
| CORRECTS | 8 |
| DECIDES | 6 |
| DERIVED_FROM | 4 |
| PUBLISHED_IN | 5 |
| RECORDED | 8 |
| SUPPORTED_BY | 18 |
| USED_OUTPUT | 253 |
| VALIDATES | 6 |

## Judgments by mode (live Jev)

```cypher
MATCH (j:Judgment {tenant_id:$tenant}) RETURN j.mode AS mode,count(*) AS n
```

| mode | n |
| --- | --- |
| live | 23 |

## Runs by kind

```cypher
MATCH (r:Run {tenant_id:$tenant}) RETURN coalesce(r.run_kind,r.kind) AS kind,count(*) AS n ORDER BY kind
```

| kind | n |
| --- | --- |
| normal | 23 |
| shadow | 6 |
