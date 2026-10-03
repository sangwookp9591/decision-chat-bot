import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.getenv("JEV_MODE") != "live", reason="requires JEV_MODE=live and live Jev credentials")


def test_two_live_request_shapes():
    from jevtriage.config import get_settings
    from jevtriage.judgment.jev_client import JevClient
    from jevtriage.judgment.pipeline import run_judgment
    settings = get_settings()
    c = JevClient(api_key=settings.jev_api_key.get_secret_value(), mode="live")
    cases = [("aggregate", "월별 매출 데이터를 집계해 부서별 리포트로 제공한다."), ("forecast_alert", "수요 예측 결과가 기준을 넘으면 운영 담당자에게 알림을 보낸다.")]
    results = {}
    for name, text in cases:
        results[name] = run_judgment([], text, {"auto_assign_enabled":False,"catalog_noul_threshold":0.4}, c)
    out = Path(__file__).resolve().parents[3] / "artifacts/validation/t03"; out.mkdir(parents=True, exist_ok=True)
    (out/"live-smoke.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    assert results["aggregate"]["draft_tasks"] != results["forecast_alert"]["draft_tasks"]
