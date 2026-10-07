"""Official Python MCP SDK transport; dev identity is an explicit local-only opt-in."""

from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from time import monotonic
from typing import Annotated, Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from ildongi.auth.service import dev_principal
from ildongi.mcp_server import service


class McpSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore")
    mcp_sse_enabled: bool = False
    mcp_allow_submit: bool = False
    mcp_auth_mode: str = ""
    mcp_dev_user: str = "requester@t-alpha.dev"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8787, ge=1, le=65535)

    @field_validator("mcp_auth_mode")
    @classmethod
    def require_dev(cls, value):
        if value != "dev":
            raise ValueError("MCP_AUTH_MODE=dev를 명시해야 서버를 시작할 수 있습니다.")
        return value

    @field_validator("mcp_host")
    @classmethod
    def loopback_only(cls, value):
        if value != "127.0.0.1":
            raise ValueError("개발 MCP는 127.0.0.1 바인딩만 허용합니다.")
        return value

    @field_validator("mcp_dev_user")
    @classmethod
    def nonempty_user(cls, value):
        if not value.strip():
            raise ValueError("MCP_DEV_USER는 비어 있을 수 없습니다.")
        return value.strip()


class SubmissionResult(BaseModel):
    summary: str = Field(description="사람이 읽을 접수 요약")
    request_id: str
    status: str
    run_id: str | None = None
    job_id: str | None = None
    revision_id: str | None = None


class RequestResult(BaseModel):
    summary: str
    request_id: str
    status: str
    request: dict[str, Any] = Field(description="권한에 따라 원문이 제거된 요청 상세")
    progress: dict[str, Any] | None = Field(description="진행 단계와 잠정 분류·신뢰도")
    judgment: dict[str, Any] | None = Field(
        description="최종 분류 ai_need/feasibility/urgency/lead_org, outputs 신뢰도, rule_effects, draft_tasks")


class RequestsResult(BaseModel):
    summary: str
    items: list[dict[str, Any]]


class ReviewsResult(BaseModel):
    summary: str
    reviews: list[dict[str, Any]]


class TasksResult(BaseModel):
    summary: str
    tasks: list[dict[str, Any]]


MAX_REQUEST_BYTES = 16_384
MAX_RESULT_BYTES = 524_288
MAX_RESULTS = 10
Limit = Annotated[int, Field(ge=1, le=MAX_RESULTS, description="최대 조회 건수(1~10)")]


def result(model: BaseModel) -> CallToolResult:
    response = CallToolResult(content=[TextContent(type="text", text=model.summary)],
                              structuredContent=model.model_dump(mode="json"))
    if len(response.model_dump_json().encode()) > MAX_RESULT_BYTES:
        raise ToolError("결과 크기 제한을 초과했습니다. 조회 범위를 줄이세요.")
    return response


async def invoke(ctx: Context, function, *args):
    try:
        # Re-resolve membership on every call so disabled accounts/changed grants take effect.
        principal = await dev_principal(ctx.request_context.lifespan_context["email"])
        return await function(principal, *args)
    except Exception:  # noqa: BLE001 - transport boundary must never echo credentials/source
        # Driver/SDK exceptions may contain provider credentials or raw source: never echo them.
        raise ToolError("일동이 요청을 처리할 수 없습니다. 사용자 권한·요청 ID·DB 상태를 확인하세요.") from None


class RequestLimits:
    """One shared budget across both transports; never trust forwarded client identities."""

    def __init__(self, app):
        self.app = app
        self.started = monotonic()
        self.count = self.active = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] not in {"/mcp", "/mcp/stream"}:
            return await self.app(scope, receive, send)
        async def reject(message):
            await JSONResponse({"error": message}, status_code=429,
                               headers={"Retry-After": "60", "Cache-Control": "no-store"})(scope, receive, send)
        now = monotonic()
        if now - self.started >= 60:
            self.started, self.count = now, 0
        # ponytail: single-process budget; use gateway limits before running multiple workers.
        self.count += 1
        if self.count > 60 or self.active >= 4:
            return await reject("요청 제한을 초과했습니다.")
        self.active += 1
        try:
            messages, size = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                size += len(message.get("body", b""))
                if size > MAX_REQUEST_BYTES:
                    return await reject("본문 크기 제한을 초과했습니다.")
                messages.append(message)
                if not message.get("more_body", False):
                    break
            async def replay():
                return messages.pop(0) if messages else await receive()
            await self.app(scope, replay, send)
        finally:
            self.active -= 1


class DevMCP(FastMCP):
    def streamable_http_app(self):
        app = super().streamable_http_app()
        if self.sse_enabled:
            stream = StreamableHTTPSessionManager(
                app=self._mcp_server, json_response=False, stateless=True,
                security_settings=self.settings.transport_security,
                max_request_body_size=MAX_REQUEST_BYTES)
            app.routes.append(Route("/mcp/stream", endpoint=StreamableHTTPASGIApp(stream)))
            @asynccontextmanager
            async def lifespan(app):
                async with AsyncExitStack() as stack:
                    await stack.enter_async_context(self.session_manager.run())
                    await stack.enter_async_context(stream.run())
                    yield
            app.router.lifespan_context = lifespan
        app.add_middleware(RequestLimits)
        return app

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        try:
            return await super().call_tool(name, arguments)
        except Exception:  # noqa: BLE001 - SDK validation errors may contain raw input
            return CallToolResult(isError=True, content=[TextContent(
                type="text", text="도구 입력·사용자 권한·요청 ID·DB 상태를 확인하세요.")])


def create_server(settings: McpSettings | None = None) -> FastMCP:
    settings = settings or McpSettings()

    @asynccontextmanager
    async def lifespan(server):
        await dev_principal(settings.mcp_dev_user)
        yield {"email": settings.mcp_dev_user}

    mcp = DevMCP("일동이", host=settings.mcp_host, port=settings.mcp_port,
                  streamable_http_path="/mcp", stateless_http=True, json_response=True,
                  lifespan=lifespan, log_level="WARNING", max_request_body_size=MAX_REQUEST_BYTES,
                  instructions="업무 요청을 접수하고 판단·검토·업무 상태를 조회합니다. 판단은 잠정/최종을 구분합니다.")
    mcp.sse_enabled = settings.mcp_sse_enabled
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                           idempotentHint=True, openWorldHint=False)

    async def submit_request(text: Annotated[str, Field(min_length=1, max_length=20_000,
                                                      description="접수할 업무 요청 내용")],
                             ctx: Context) -> SubmissionResult:
        data = await invoke(ctx, service.submit_request, text)
        return result(SubmissionResult(summary=f"업무 요청 {data['request_id']}을 접수했습니다.",
                                       **data))

    if settings.mcp_allow_submit:
        mcp.add_tool(submit_request, description="업무 요청을 접수합니다. 재호출은 새 요청을 만듭니다.",
                     annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                                 idempotentHint=False, openWorldHint=False))

    @mcp.tool(description="요청 진행 상태와 잠정/최종 판단(4개 분류·신뢰도), 적용 규칙, 업무 초안을 조회합니다.",
              annotations=read)
    async def get_request_result(request_id: Annotated[str, Field(min_length=1, max_length=200,
                                                               description="접수된 요청 ID")],
                                 ctx: Context) -> RequestResult:
        data = await invoke(ctx, service.get_request_result, request_id)
        final = data["judgment"]
        summary = f"요청 {request_id}: {data['status']} · {'최종 판단' if final else '처리 중/잠정 판단'}"
        if final:
            summary += "\n" + ", ".join(f"{k}: {v}" for k, v in final["classifications"].items())
        return result(RequestResult(summary=summary, **data))

    @mcp.tool(description="웹 API와 동일하게 본인과 공유 조직의 권한 있는 요청 목록을 조회합니다.", annotations=read)
    async def list_my_requests(ctx: Context, limit: Limit = MAX_RESULTS) -> RequestsResult:
        data = await invoke(ctx, service.list_my_requests, limit)
        return result(RequestsResult(summary=f"조회 가능한 요청 {len(data['items'])}건입니다.", **data))

    @mcp.tool(description="본인 검토 조직의 대기 목록을 조회합니다. 검토자 권한이 없으면 빈 목록입니다.", annotations=read)
    async def list_review_queue(ctx: Context, limit: Limit = MAX_RESULTS) -> ReviewsResult:
        data = await invoke(ctx, service.list_review_queue, limit)
        return result(ReviewsResult(summary=f"검토 대기 {len(data['reviews'])}건입니다.", **data))

    @mcp.tool(description="본인 조직·역할로 조회 가능한 배정 업무 목록을 조회합니다.", annotations=read)
    async def list_tasks(ctx: Context, limit: Limit = MAX_RESULTS) -> TasksResult:
        data = await invoke(ctx, service.list_tasks, limit)
        return result(TasksResult(summary=f"조회 가능한 업무 {len(data['tasks'])}건입니다.", **data))

    @mcp.custom_route("/", methods=["GET"])
    async def health(request):
        return PlainTextResponse("일동이 개발 MCP")

    # Starlette's unmatched routes return 404 for unused /.well-known/oauth-* discovery.
    return mcp
