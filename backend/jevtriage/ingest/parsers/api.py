from __future__ import annotations

import multiprocessing
import os
import signal
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from jevtriage.ingest.files import hash_file

Status = Literal["ok", "rejected"]
Reason = Literal[
    "too_large",
    "too_many_pages",
    "encrypted",
    "corrupted",
    "unsupported_type",
    "scanned_no_text",
    "archive_bomb",
    "timeout",
    "memory_limit",
]
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 25 * 1024 * 1024
MAX_ATTACHMENTS = 5
MAX_TEXT_CHARS = 20_000
MAX_PDF_PAGES = 50
MAX_ARCHIVE_EXPANDED = 50 * 1024 * 1024
MAX_ARCHIVE_RATIO = 100
PARSE_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Unit:
    unit_id: str
    text: str
    location: dict[str, str | int]
    char_start: int
    char_end: int


@dataclass(frozen=True)
class ExtractionResult:
    status: Status
    reason: Reason | None
    units: list[Unit]
    char_count: int
    page_count: int | None
    sha256: str
    byte_count: int = 0


@dataclass(frozen=True)
class LimitVerdict:
    allowed: bool
    reason: str | None
    char_count: int


class _Rejected(Exception):
    def __init__(self, reason: Reason):
        self.reason = reason


def _hash(path: Path) -> str:
    return hash_file(path)


def _kind(path: Path) -> str:
    with path.open("rb") as f:
        head = f.read(8)
    suffix = path.suffix.lower()
    if head.startswith(b"%PDF-"):
        kind = "pdf"
    elif head.startswith(b"PK\x03\x04"):
        kind = "docx"
    elif suffix == ".md" and not head.startswith((b"\x89PNG", b"GIF8", b"\xff\xd8")):
        kind = "md"
    else:
        raise _Rejected("unsupported_type")
    if suffix != f".{kind}":
        raise _Rejected("unsupported_type")
    return kind


def _docx_archive_check(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            expanded = sum(entry.file_size for entry in entries)
            if expanded > MAX_ARCHIVE_EXPANDED or any(
                entry.file_size > 0
                and entry.file_size / max(entry.compress_size, 1) > MAX_ARCHIVE_RATIO
                for entry in entries
            ):
                raise _Rejected("archive_bomb")
            names = {item.filename for item in entries}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise _Rejected("corrupted")
    except _Rejected:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError):
        raise _Rejected("corrupted")


def _extract(path: Path, display_name: str) -> tuple[list[Unit], int | None]:
    kind = _kind(path)
    units: list[Unit] = []
    offset = 0
    if kind == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path), strict=True)
            if reader.is_encrypted:
                try:
                    if reader.decrypt("") == 0:
                        raise _Rejected("encrypted")
                except _Rejected:
                    raise
                except Exception:  # noqa: BLE001 - parser library has varied decryption exceptions
                    raise _Rejected("encrypted")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise _Rejected("too_many_pages")
            for page_no, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    units.append(
                        Unit(
                            f"p{page_no}",
                            text,
                            {"file": display_name, "page": page_no},
                            offset,
                            offset + len(text),
                        )
                    )
                    offset += len(text)
            if not units:
                raise _Rejected("scanned_no_text")
            return units, len(reader.pages)
        except _Rejected:
            raise
        except Exception:  # noqa: BLE001 - malformed PDF exceptions vary by library version
            raise _Rejected("corrupted")
    if kind == "docx":
        _docx_archive_check(path)
        try:
            from docx import Document

            document = Document(str(path))
            for index, paragraph in enumerate(document.paragraphs):
                text = paragraph.text
                if text:
                    units.append(
                        Unit(
                            f"para{index}",
                            text,
                            {"file": display_name, "paragraph": index},
                            offset,
                            offset + len(text),
                        )
                    )
                    offset += len(text)
            if not units:
                raise _Rejected("scanned_no_text")
            return units, None
        except _Rejected:
            raise
        except Exception:  # noqa: BLE001 - malformed OOXML exceptions vary by library version
            raise _Rejected("corrupted")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise _Rejected("corrupted")
    except OSError:
        raise _Rejected("corrupted")
    lines = text.splitlines(keepends=True)
    for ix, line in enumerate(lines, 1):
        body = line.rstrip("\r\n")
        if body:
            units.append(
                Unit(
                    f"line{ix}",
                    body,
                    {"file": display_name, "line_start": ix, "line_end": ix},
                    offset,
                    offset + len(body),
                )
            )
            offset += len(body)
    if not units:
        raise _Rejected("scanned_no_text")
    return units, None


def _worker(path: str, name: str, conn) -> None:
    try:
        if os.name == "posix":
            try:
                import resource

                limit = 512 * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
            except (ImportError, OSError, ValueError):
                pass
        units, pages = _extract(Path(path), name)
        conn.send(("ok", units, pages))
    except _Rejected as exc:
        conn.send(("rejected", exc.reason, None))
    except MemoryError:
        conn.send(("rejected", "memory_limit", None))
    except Exception:  # noqa: BLE001 - isolate arbitrary parser failures at process boundary
        conn.send(("rejected", "corrupted", None))
    finally:
        conn.close()


def parse_file(
    path: str | Path, filename: str, declared_mime: str | None = None
) -> ExtractionResult:
    """Parse a supported file in a resource-limited spawned process."""
    file_path = Path(path)
    digest = _hash(file_path) if file_path.is_file() else ""
    if not file_path.is_file() or file_path.stat().st_size > MAX_FILE_BYTES:
        return ExtractionResult(
            "rejected",
            "too_large",
            [],
            0,
            None,
            digest,
            file_path.stat().st_size if file_path.is_file() else 0,
        )
    byte_count = file_path.stat().st_size
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(str(file_path), filename, child))
    process.start()
    child.close()
    process.join(PARSE_TIMEOUT_SECONDS)
    if process.is_alive():
        process.terminate()
        process.join(2)
        return ExtractionResult("rejected", "timeout", [], 0, None, digest, byte_count)
    if parent.poll():
        payload = parent.recv()
        parent.close()
        if payload[0] == "rejected":
            return ExtractionResult("rejected", payload[1], [], 0, None, digest, byte_count)
        units, pages = payload[1], payload[2]
        return ExtractionResult(
            "ok", None, units, sum(len(u.text) for u in units), pages, digest, byte_count
        )
    parent.close()
    reason: Reason = (
        "memory_limit" if process.exitcode in (-signal.SIGKILL, -signal.SIGSEGV) else "corrupted"
    )
    return ExtractionResult("rejected", reason, [], 0, None, digest, byte_count)


def check_request_limits(results: list[ExtractionResult], chat_text: str) -> LimitVerdict:
    if len(results) > MAX_ATTACHMENTS:
        return LimitVerdict(
            False, "too_many_attachments", sum(r.char_count for r in results) + len(chat_text)
        )
    chars = sum(r.char_count for r in results) + len(chat_text)
    if sum(result.byte_count for result in results) > MAX_TOTAL_BYTES:
        return LimitVerdict(False, "too_many_bytes", chars)
    if chars > MAX_TEXT_CHARS:
        return LimitVerdict(False, "too_many_characters", chars)
    if any(r.status != "ok" for r in results):
        return LimitVerdict(False, "attachment_rejected", chars)
    return LimitVerdict(True, None, chars)
