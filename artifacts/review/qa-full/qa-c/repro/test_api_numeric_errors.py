"""QA-C-05: invalid numeric JSON input must produce 4xx, never serializer 500."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jevtriage.config import get_settings
from jevtriage.main import create_app

EVIDENCE=Path(__file__).resolve().parents[1]/'evidence'


@pytest.mark.parametrize('number',['1e1000','NaN','Infinity','-Infinity'])
def test_invalid_login_numeric_value_does_not_produce_500(number,monkeypatch,tmp_path,request):
    monkeypatch.setenv('DATA_DIR',str(tmp_path))
    get_settings.cache_clear()
    request.addfinalizer(get_settings.cache_clear)
    with TestClient(create_app(),raise_server_exceptions=False) as c:
        r=c.post('/api/auth/login',content='{"email":'+number+',"password":"qa-only"}',
                 headers={'Content-Type':'application/json'})
    with (EVIDENCE/'numeric-validation.jsonl').open('a') as out:
        out.write(json.dumps({'json_number':number,'status':r.status_code,'body':r.text})+'\n')
    assert 400<=r.status_code<500, f'invalid numeric field produced {r.status_code}'
