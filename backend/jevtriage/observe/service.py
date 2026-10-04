"""Public trace write boundary used by the job runtime."""

from jevtriage.observe.trace_store import finish_step_in_tx as _finish_step_in_tx
from jevtriage.observe.trace_store import start_step_in_tx as _start_step_in_tx


async def start_step_in_tx(tx, **kwargs):
    return await _start_step_in_tx(tx, **kwargs)


async def finish_step_in_tx(tx, **kwargs):
    return await _finish_step_in_tx(tx, **kwargs)
