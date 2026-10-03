# DB 질의 결과 요약 (T38)

tenant `t-x38r-10031227` — 읽기 전용 Cypher, 값은 질의 실행 시점의 Neo4j 저장 결과.

## Correction (X01)

```cypher
MATCH (h:ReviewDecision {tenant_id:$tenant})-[:RECORDED]->(c:Correction) RETURN c.id,c.request_id,c.field,c.ai_value,c.corrected_value,c.corrected_by,c.run_id,c.config_version,size(c.evidence_span_ids) AS spans ORDER BY c.corrected_at
```

| c.id | c.request_id | c.field | c.ai_value | c.corrected_value | c.corrected_by | c.run_id | c.config_version | spans |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cor_e1c531571fd64851b38fb3f407ad7ff9 | req_e5a4b6149b7a4a468bc95b086a2bfd7e | ai_need | "불필요" | "필요" | usr_t-x38r-10031227_reviewer | run_b3e6a3027d744d8e972f0a999631de78 | 1 | 0 |
| cor_a12d0808c0124f07baf6b7d73b7663b8 | req_b94acf8a7799418e83ed3ce36b33e30b | ai_need | "불필요" | "필요" | usr_t-x38r-10031227_reviewer | run_f9904b08f4ad46aeb19f3c3f61d73c1b | 1 | 0 |
| cor_e4a28aea4e6c4d4880eb64292314cdc1 | req_31aeb1815a934213b2021a8a332e223c | ai_need | "불필요" | "필요" | usr_t-x38r-10031227_reviewer | run_ee52a1ccef9b42d4a31203c5f08e9eb2 | 1 | 0 |
| cor_f0817ad4222842cf9d759be1a3e4e647 | req_e13745e1a3324d48812e6baef41f3ada | ai_need | "불필요" | "혼합" | usr_t-x38r-10031227_reviewer | run_ab12ee5450ad4e89b02353b250f37d8e | 1 | 0 |
| cor_58af725183634ae9aeaa16b373a5f990 | req_2744ff85abff43d18524b8fbff205485 | ai_need | "불필요" | "혼합" | usr_t-x38r-10031227_reviewer | run_9b2d04842f38492fbb92687b8dd98874 | 1 | 0 |
| cor_503b976a073f4aef9f95a2f9474ca09b | req_44f8f9b084594f8187684e9781f642fb | lead_org | "IT팀" | "현업" | usr_t-x38r-10031227_reviewer | run_87b928775dd441aab961db472e20131a | 2 | 0 |
| cor_382a770a59a5438682cf9d5a21d0a74d | req_f893e67063944583806ba8391bee4914 | lead_org | "IT팀" | "현업" | usr_t-x38r-10031227_reviewer | run_08eb9405a8e449a4bb2767ba8222a7e4 | 2 | 0 |
| cor_a2f1d4fe9a4c4f919deefe62082320a3 | req_bef8e1a8aa97464aaf1dcb1d0586db4e | lead_org | "IT팀" | "현업" | usr_t-x38r-10031227_reviewer | run_940aae3c02ce43deb04f4454d0500669 | 2 | 0 |
| cor_f3c482e76e094ce5825c7264717b5d06 | req_7c3fde8d66cb4f708cd0112299129235 | feasibility | "정보 부족" | "조건부 가능" | usr_t-x38r-10031227_reviewer | run_14b3672bb391453bbe1753afbe70697a | 3 | 1 |
| cor_f53eaee7e65f4d4a97866d464f631bec | req_1af31c93fd864e398be8734a8e0787c8 | feasibility | "정보 부족" | "조건부 가능" | usr_t-x38r-10031227_reviewer | run_9ca99cb1506740b9b110dee76c5f17ce | 3 | 1 |
| cor_88104cfdf04742de93884ec0aa95a41f | req_be8192ae007e4a7c92089b38c3aef6ea | feasibility | "정보 부족" | "조건부 가능" | usr_t-x38r-10031227_reviewer | run_65f93e7e6f9145f2badd61cfeb35d552 | 3 | 1 |

## Candidate links (X02)

```cypher
MATCH (n:RuleCandidate {tenant_id:$tenant})-[r:SUPPORTED_BY]->(x) RETURN n.id,n.field,n.status,r.role,labels(x)[0] AS label,count(*) AS n ORDER BY n.id,r.role
```

| n.id | n.field | n.status | r.role | label | n |
| --- | --- | --- | --- | --- | --- |
| cand_79f6d9ca44e33854681ab0b0 | feasibility | approved | counter | ReviewDecision | 3 |
| cand_79f6d9ca44e33854681ab0b0 | feasibility | approved | support | Correction | 3 |
| cand_8fcc507094e6868374ddec5c | ai_need | approved | counter | ReviewDecision | 4 |
| cand_8fcc507094e6868374ddec5c | ai_need | approved | support | Correction | 3 |
| cand_9a49449bb55ab51162c213e0 | lead_org | approved | counter | ReviewDecision | 3 |
| cand_9a49449bb55ab51162c213e0 | lead_org | approved | support | Correction | 3 |
| cand_e123faef72028b6d12635bef | ai_need | approved | counter | ReviewDecision | 5 |
| cand_e123faef72028b6d12635bef | ai_need | approved | support | Correction | 2 |

## Rule decisions (X03)

```cypher
MATCH (d:RuleDecision {tenant_id:$tenant})-[:DECIDES]->(c:RuleCandidate) RETURN d.id,c.id AS candidate,d.action,d.decided_by,d.confirmed_scope IS NOT NULL AS has_scope ORDER BY d.decided_at
```

| d.id | candidate | d.action | d.decided_by | has_scope |
| --- | --- | --- | --- | --- |
| rdec_f01ba658005b4be0bbc4f24cb8accb2f | cand_8fcc507094e6868374ddec5c | approve_with_scope_change | usr_t-x38r-10031227_rule_admin | True |
| rdec_86485b0355534353b4d3a4aec8ade3c1 | cand_e123faef72028b6d12635bef | approve | usr_t-x38r-10031227_rule_admin | True |
| rdec_16b2b896cc344614b98c2423db381d52 | cand_9a49449bb55ab51162c213e0 | approve | usr_t-x38r-10031227_rule_admin | True |
| rdec_65ada79162344602b90a1ae72c736684 | cand_79f6d9ca44e33854681ab0b0 | approve | usr_t-x38r-10031227_rule_admin | True |
| rdec_84495d2d93af4a2083f886cb6bfe97cc | cand_0c4749cc88828c487a3d8ead | approve | usr_t-x38r-10031227_rule_admin | True |
| rdec_0861c5d6162c450f97910ca9e7157469 | cand_c17cccefbccbc8ec2ba3f9c2 | reject | usr_t-x38r-10031227_rule_admin | True |

## Rule versions and publication

```cypher
MATCH (r:RuleVersion {tenant_id:$tenant}) OPTIONAL MATCH (r)-[:PUBLISHED_IN]->(c:ConfigVersion) RETURN r.id,r.status,collect(c.version) AS configs ORDER BY r.id
```

| r.id | r.status | configs |
| --- | --- | --- |
| R-AI_NEED-01@1 | published | [9, 7, 2] |
| R-AI_NEED-01@2 | reverted | [6] |
| R-AI_NEED-02@1 | validating | [] |
| R-AI_NEED-03@1 | validating | [] |
| R-FEASIBILITY-01@1 | published | [4] |
| R-LEAD_ORG-01@1 | published | [3] |

## Config versions

```cypher
MATCH (c:ConfigVersion {tenant_id:$tenant}) RETURN c.version,c.status,c.created_by,c.reason ORDER BY c.version
```

| c.version | c.status | c.created_by | c.reason |
| --- | --- | --- | --- |
| 1 | superseded | system:bootstrap | 보수적 초기 정책 |
| 2 | superseded | usr_t-x38r-10031227_rule_admin | T38: 게시 |
| 3 | superseded | usr_t-x38r-10031227_rule_admin | T38-R: 게시 |
| 4 | superseded | usr_t-x38r-10031227_rule_admin | T38-R: 게시 |
| 5 | superseded | usr_t-x38r-10031227_rule_admin | T38: 중단(진행 중 실행 시험) |
| 6 | superseded | usr_t-x38r-10031227_rule_admin | T38: v2 게시 |
| 7 | superseded | usr_t-x38r-10031227_rule_admin | T38: v1로 되돌리기 |
| 8 | superseded | usr_t-x38r-10031227_rule_admin | T38: 진행 중 실행 시험 1 |
| 9 | active | usr_t-x38r-10031227_rule_admin | T38: 시험 후 v1 복원 |

## ValidationRun (X04)

```cypher
MATCH (v:ValidationRun {tenant_id:$tenant}) RETURN v.id,v.rule_version,v.status,v.run_kind,v.sample_count,v.labeled_count,v.changed_count,v.side_effects ORDER BY v.created_at
```

| v.id | v.rule_version | v.status | v.run_kind | v.sample_count | v.labeled_count | v.changed_count | v.side_effects |
| --- | --- | --- | --- | --- | --- | --- | --- |
| val_ae2b8a074e3d412aa003c57a6efab5d4 | R-AI_NEED-01@1 | completed | shadow | 8 | 7 | 8 | 0 |
| val_e8697532f8bc4b8cabcee5205d372aba | R-LEAD_ORG-01@1 | completed | shadow | 18 | 13 | 6 | 0 |
| val_c9703714627f4b33862c115123f71ef8 | R-FEASIBILITY-01@1 | completed | shadow | 31 | 19 | 20 | 0 |
| val_7c3f38b9de3c4741b418b6198f00fcdd | R-AI_NEED-01@2 | completed | shadow | 34 | 19 | 10 | 0 |
| val_84f211ef173545f4929360f37b2cd600 | R-AI_NEED-02@1 | completed | shadow | 37 | 19 | 0 | 0 |

## RuleApplication (X05/X07)

```cypher
MATCH (s:RunStep {tenant_id:$tenant})-[a:APPLIED]->(rv:RuleVersion) RETURN rv.id AS rule,a.outcome,count(*) AS n ORDER BY rule,a.outcome
```

| rule | a.outcome | n |
| --- | --- | --- |
| R-AI_NEED-01@1 | out_of_scope | 8 |
| R-AI_NEED-01@1 | used | 19 |
| R-AI_NEED-01@2 | used | 1 |
| R-FEASIBILITY-01@1 | out_of_scope | 6 |
| R-FEASIBILITY-01@1 | used | 1 |
| R-LEAD_ORG-01@1 | out_of_scope | 19 |
| R-LEAD_ORG-01@1 | used | 1 |

## Audit by action

```cypher
MATCH (a:Audit {tenant_id:$tenant}) WHERE a.action STARTS WITH 'rule.' RETURN a.action,count(*) AS n ORDER BY a.action
```

| a.action | n |
| --- | --- |
| rule.decision | 6 |
| rule.publish | 4 |
| rule.revert | 2 |
| rule.stop | 2 |
| rule.validated | 4 |
| rule.version_created | 6 |

## Events by kind (rule.*)

```cypher
MATCH (e:Event {tenant_id:$tenant}) WHERE e.kind STARTS WITH 'rule.' RETURN e.kind,count(*) AS n ORDER BY e.kind
```

| e.kind | n |
| --- | --- |
| rule.decision | 6 |
| rule.publish | 4 |
| rule.revert | 2 |
| rule.stop | 2 |
| rule.validated | 4 |
| rule.version_created | 6 |

## Graph relationships among learning nodes

```cypher
MATCH (a {tenant_id:$tenant})-[r]->(b {tenant_id:$tenant}) WHERE type(r) IN ['CITES','CORRECTS','RECORDED','SUPPORTED_BY','DECIDES','DERIVED_FROM','PUBLISHED_IN','VALIDATES','APPLIED','USED_OUTPUT'] RETURN type(r) AS type,count(*) AS n ORDER BY type
```

| type | n |
| --- | --- |
| APPLIED | 55 |
| CITES | 46 |
| CORRECTS | 11 |
| DECIDES | 6 |
| DERIVED_FROM | 6 |
| PUBLISHED_IN | 6 |
| RECORDED | 11 |
| SUPPORTED_BY | 26 |
| USED_OUTPUT | 418 |
| VALIDATES | 5 |

## Judgments by mode (live Jev)

```cypher
MATCH (j:Judgment {tenant_id:$tenant}) RETURN j.mode AS mode,count(*) AS n
```

| mode | n |
| --- | --- |
| live | 38 |

## Runs by kind

```cypher
MATCH (r:Run {tenant_id:$tenant}) RETURN coalesce(r.run_kind,r.kind) AS kind,count(*) AS n ORDER BY kind
```

| kind | n |
| --- | --- |
| normal | 38 |
| shadow | 5 |
