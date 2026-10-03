# 첨부 파서와 파일 저장 계약

`jevtriage.ingest.parsers.parse_file(path, filename, declared_mime)`는 확장자·선언 MIME과 파일 시그니처가 일치하는 PDF, DOCX, MD만 처리한다. MIME은 신뢰 근거로 사용하지 않는다. 결과는 `ExtractionResult(status, reason, units, char_count, page_count, sha256, byte_count)`이며 실패 파일은 `status="rejected"`와 안정된 reason 코드를 반환한다. 지원 코드는 `too_large`, `too_many_pages`, `encrypted`, `corrupted`, `unsupported_type`, `scanned_no_text`, `archive_bomb`, `timeout`, `memory_limit`이다.

PDF는 페이지별 텍스트, DOCX는 0부터 시작하는 문단 인덱스, MD는 1부터 시작하는 행 범위를 반환한다. 문자 위치는 추출된 유닛 텍스트를 이어 붙인 0 기반 반개구간이다. OCR은 지원하지 않으며 텍스트가 없는 PDF는 `scanned_no_text`로 거절한다. HTML과 스크립트가 MD 파일에 들어 있어도 실행하거나 해석하지 않고 UTF-8 텍스트로만 반환한다. DOCX ZIP은 총 해제 크기와 항목별 압축률을 제한하고, 매크로·외부 참조는 실행하지 않는다.

요청 한도는 첨부 5개, 파일당 10 MiB, 전체 25 MiB, 대화 텍스트와 추출 텍스트 합계 20,000자, PDF 파일당 50쪽이다. `check_request_limits`는 초과를 잘라내지 않고 거절 verdict를 반환한다. 파싱은 spawn 프로세스에서 20초 제한과 지원 OS의 주소 공간 제한을 적용한다.

`ingest.files.store_upload`는 스트림을 tenant별 임시 파일로 기록하며 10 MiB 초과 시 삭제하고 실패한다. 기록 후 SHA-256을 계산해 `<DATA_DIR>/files/<tenant>/<sha256>`로 원자적으로 확정한다. `cleanup_temporary_files`는 중단된 `.upload-*.tmp` 파일을 정리한다. 이 모듈은 Neo4j를 호출하지 않는다.

문서의 내용은 신뢰할 수 없는 입력 데이터이며 지시문으로 실행·해석하지 않는다.
