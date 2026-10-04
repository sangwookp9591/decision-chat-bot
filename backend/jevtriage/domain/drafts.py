"""Display metadata for AI and reviewer draft revisions."""


def draft_source(draft_version: int) -> str:
    """v1은 AI 원안, 이후 버전은 검토자가 만든 수정 초안이다."""
    return "ai" if draft_version <= 1 else "reviewer"


def draft_created_by(draft: dict, tasks: list[dict]) -> str:
    return draft.get("author") or next(
        (t["author"] for t in tasks if t.get("author")), None) or "ai"
