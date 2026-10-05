# QA-A2 execution notes

- Diagnostic attempt `20261005T194718`: encrypted-PDF fixture failed HTTP 500 because the QA diagnostic launcher lacked a `__main__` guard. The spawned parser re-executed uvicorn and attempted binding 11291; EOFError followed. This is harness failure, not counted as product defect.
- Same test after the QA launcher guard: `20261005T194815`, 1 passed (8.9s), encrypted file exclusion and result succeeded. No database timeout.
- Full Chromium run `20261005T194843`, tenant `t-qa-a-1005194843`, 61 collected cases, one worker, mock.
- Confirmed first failures: task detail remains open after Escape; task detail in first tab remains on waiting after second tab moves to in-progress. Screenshots in run acceptance folder; product files unchanged.
