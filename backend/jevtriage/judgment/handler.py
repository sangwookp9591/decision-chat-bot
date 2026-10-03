"""Registered worker entrypoint for judgment jobs."""
from jevtriage.judgment.service import execute_judgment


async def handle_judgment(ctx):
    await execute_judgment(ctx)
