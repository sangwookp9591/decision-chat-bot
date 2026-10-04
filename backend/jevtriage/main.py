import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from jevtriage import api_encoding  # noqa: F401  (registers Neo4j temporal JSON encoders)
from jevtriage.auth.core import enforce_csrf
from jevtriage.auth.router import router as auth_router
from jevtriage.config import get_settings
from jevtriage.db.driver import create_driver
from jevtriage.domain.ids import new_id
from jevtriage.evaluation.api import router as evaluation_router
from jevtriage.events.router import router as events_router
from jevtriage.graph.api import router as graph_router
from jevtriage.ingest.api import router as ingest_router
from jevtriage.journal.reader import producer_heartbeat
from jevtriage.journal.writer import JournalWriter, failure_count, flush_all
from jevtriage.judgment.api import router as judgment_router
from jevtriage.judgment.progress import router as progress_router
from jevtriage.learning.candidates_api import request_router as request_learning_router
from jevtriage.learning.candidates_api import router as learning_router
from jevtriage.learning.effects_api import router as effects_router
from jevtriage.learning.rules_api import router as learning_rules_router
from jevtriage.learning.shadow_api import router as shadow_router
from jevtriage.learning.shadow_api import validation_router
from jevtriage.monitoring.api import router as monitoring_router
from jevtriage.observe.api import router as observe_router
from jevtriage.policy.router import router as policy_router
from jevtriage.review.api import router as review_router
from jevtriage.tasks.api import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.neo4j_driver = create_driver(get_settings())
    async def api_heartbeat() -> None:
        while True:
            try:
                producer_heartbeat(get_settings().data_dir, "api", failure_count())
            except OSError:
                pass  # Disk-space alert is emitted by the independent watchdog.
            await asyncio.sleep(5)

    heartbeat_task = asyncio.create_task(api_heartbeat())
    try:
        yield
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task
        await asyncio.to_thread(flush_all)
        await app.state.neo4j_driver.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Jev Triage API", lifespan=lifespan)
    app.include_router(auth_router)
    app.include_router(ingest_router)
    app.include_router(judgment_router)
    app.include_router(progress_router)
    app.include_router(learning_rules_router)
    app.include_router(shadow_router)
    app.include_router(validation_router)
    app.include_router(effects_router)
    app.include_router(events_router)
    app.include_router(evaluation_router)
    app.include_router(policy_router)
    app.include_router(monitoring_router)
    app.include_router(review_router)
    app.include_router(observe_router)
    app.include_router(learning_router)
    app.include_router(request_learning_router)
    app.include_router(tasks_router)
    app.include_router(graph_router)

    @app.middleware("http")
    async def csrf_guard(request: Request, call_next):
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and request.url.path != "/api/auth/login"
            and request.cookies.get("jev_session")
        ):
            try:
                await asyncio.wait_for(
                    enforce_csrf(request), timeout=get_settings().auth_db_timeout_seconds)
            except HTTPException as exc:
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        return await call_next(request)

    @app.middleware("http")
    async def journal_boundary(request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        attempt = new_id("attempt")
        started = time.monotonic()
        journal = JournalWriter()
        received_at = datetime.now(UTC).isoformat()
        journal.append({"event_id": new_id("event"), "attempt_id": attempt,
                        "kind": "api_boundary_received", "ts": received_at,
                        "validity": "undetermined"})
        status = 500
        error_class = None
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except (ServiceUnavailable, SessionExpired, TimeoutError):
            status = 503
            error_class = "database_unavailable"
            if request.url.path == "/api/requests" and request.method == "POST":
                journal.append({"event_id": new_id("event"), "attempt_id": attempt,
                                "kind": "request_received", "ts": received_at,
                                "validity": "undetermined"})
                journal.append({"event_id": new_id("event"), "attempt_id": attempt,
                                "kind": "request_failed", "ts": datetime.now(UTC).isoformat(),
                                "status_code": 503, "error_class": error_class,
                                "duration_ms": round((time.monotonic() - started) * 1000),
                                "validity": "undetermined"})
            return JSONResponse(status_code=503, content={
                "detail": "Business database unavailable", "code": "db_unavailable"})
        except Exception as exc:
            error_class = type(exc).__name__
            raise
        finally:
            journal.append({"event_id": new_id("event"), "attempt_id": attempt,
                            "kind": "api_boundary_completed", "ts": datetime.now(UTC).isoformat(),
                            "status_code": status, "error_class": error_class,
                            "duration_ms": round((time.monotonic() - started) * 1000),
                            "validity": "undetermined"})

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/ready")
    async def ready(request: Request) -> dict[str, str]:
        try:
            await request.app.state.neo4j_driver.verify_connectivity()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Neo4j unavailable") from exc
        return {"status": "ready"}

    return app


app = create_app()
