"""Log only exception class/code at the ingest boundary; preserve real behavior."""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'backend'))
from jevtriage.ingest import service

original_submit = service.submit

async def submit(*args, **kwargs):
    try:
        return await original_submit(*args, **kwargs)
    except Exception as exc:
        # Never include arguments, cookies, request contents, or credentials.
        print('QA_INGEST_EXCEPTION', type(exc).__name__, getattr(exc, 'code', ''), flush=True)
        raise

service.submit = submit
if __name__ == '__main__':
    runpy.run_module('uvicorn', run_name='__main__')
