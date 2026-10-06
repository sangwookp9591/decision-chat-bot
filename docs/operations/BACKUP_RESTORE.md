# 백업과 복원

이 저장소의 Compose Neo4j는 Community 5.26.0이다. Neo4j 공식 문서에 따르면 Community `neo4j-admin database dump/load`는 데이터베이스가 offline일 때만 실행할 수 있고, 실행 중 서버에 마운트된 DB를 덤프/교체할 수 없다. 덤프에는 해당 데이터베이스 내용만 포함되며 `system` DB의 사용자·역할 메타데이터는 포함하지 않는다. 따라서 애플리케이션 writer도 정지하고 Neo4j를 내린 상태에서 백업/복원한다. 근거: [Neo4j offline backup](https://neo4j.com/docs/operations-manual/current/backup-restore/offline-backup/), [restore dump](https://neo4j.com/docs/operations-manual/current/backup-restore/restore-dump/).

## 백업

먼저 API·worker·collector·watchdog 프로세스를 정지해 파일/journal/metrics 기록을 멈춘다. 운영 백업은 반드시 전용 프로젝트 `ildongi-backup`, 컨테이너 `ildongi-backup-neo4j-1`, 호스트 Bolt 포트 7689에서 수행한다. 기본 `decision-chat-bot` Compose DB를 대상으로 하면 스크립트가 거절한다. 동일 데이터 경로를 공유 default Compose Neo4j가 사용 중인 경우에도 거절한다.

기본 개발 프로젝트가 실행 중이면 `make down`으로 먼저 정지한다. 같은 `.data/neo4j` 디렉터리를 두 Neo4j 프로세스가 동시에 열지 않는다. 이후 아래 dedicated 프로젝트만 시작한다. 앱 프로세스가 필요한 경우 그 프로세스에는 `NEO4J_URI=bolt://localhost:7689`를 환경으로 전달한다.

```sh
export NEO4J_DATA_DIR="$PWD/.data/neo4j"
export NEO4J_BOLT_PORT=7689
make down  # 기본 decision-chat-bot Neo4j 정지
docker compose -p ildongi-backup -f docker-compose.yml -f scripts/ops/compose.backup.yml up -d neo4j
# 실행 중인 서비스를 중단한 뒤 백업
make backup
# 점검 후 dedicated DB 재기동
docker compose -p ildongi-backup -f docker-compose.yml -f scripts/ops/compose.backup.yml up -d neo4j
```

`make backup`은 전용 컨테이너/프로젝트/포트를 확인하고 대상 Neo4j를 정지한 다음 고정 이미지 `neo4j:5.26.0-community`의 offline `neo4j-admin database dump neo4j`를 실행한다. 기본 결과는 `artifacts/backups/<UTC timestamp>/`다. `DATA_DIR` 기본 `.data`에서 `files`, `journal`, `metrics`, `alerts`를 각각 tar.gz로 보관하고 SHA-256 manifest를 만든다. 사용자·역할은 bootstrap으로 재생성해야 하며, 원본/journal/metrics도 민감 운영 데이터로 취급한다. 백업 디렉터리는 제한된 접근 권한으로 관리하고 암호화된 외부 저장소에 복제한다. 스크립트는 API 등 다른 프로세스를 자동 종료하지 않는다.

백업 위치를 직접 고정하려면 `make backup BACKUP_DIR=/secure/path/backup-id`를 사용한다. `NEO4J_DATA_DIR`와 `DATA_DIR`도 Make 변수로 지정할 수 있다. 스크립트 직접 실행 시 `--backup-dir`, `--container`, `--project`, `--port`, `--neo4j-volume`은 필수이며 프로젝트와 포트는 각각 `ildongi-backup`, `7689`여야 한다.

## 새 디렉터리로 복원

```sh
# 빈 경로로 복원 (RESTORE_DATA_DIR 필수)
make restore BACKUP_DIR=/secure/path/backup-id RESTORE_DATA_DIR=/srv/ildongi-restored
```

첫 대상 디렉터리는 비어 있어야 한다. 기본 Neo4j data 경로는 `<새 데이터 경로>/neo4j`다. 스크립트는 manifest 해시를 확인하고 덮어쓰기를 거부한 뒤 dump를 새 디렉터리에 load하고 파일·journal·metrics·alerts를 푼다. `make backup`/`make restore`는 프로젝트·컨테이너·포트 지정값을 검사한다. 복원된 Neo4j는 dedicated Compose project에서 `NEO4J_DATA_DIR`를 새 경로로 지정하고 port 7689로 기동한 뒤 스키마/계정을 준비하고 ID·카운트를 대조한다. 원본 운영 경로에 복원하지 않는다.

`neo4j-admin database dump`는 `system` 데이터베이스 및 사용자/역할을 포함하지 않으므로 이 스크립트의 새 경로 복원은 별도 인증/Compose 구성이 필요하다. dump/load는 Community에서 오프라인만 가능하며 온라인 무중단 백업이 아니다. 스크립트는 Neo4j를 자동으로 재기동하지 않는다.
