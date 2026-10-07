#!/usr/bin/env python3
"""Real HTTP/DB smoke with the installed official MCP SDK (one optional write)."""

import argparse
import asyncio
import json
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def check(url: str, submit: bool):
    evidence = {"url": url, "checks": {}}
    async with httpx.AsyncClient() as client:
        for path in ("/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp",
                     "/.well-known/oauth-authorization-server"):
            response = await client.get(url.removesuffix("/mcp") + path)
            assert response.status_code == 404
        evidence["checks"]["oauth_discovery_404"] = True
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            assert {t.name for t in tools} == {"get_request_result", "list_my_requests",
                                              "list_review_queue", "list_tasks"} | (
                                                  {"submit_request"} if submit else set())
            assert all(t.outputSchema and t.description for t in tools)
            assert all(t.annotations.readOnlyHint == (t.name != "submit_request") for t in tools)
            evidence["tools"] = [t.name for t in tools]
            evidence["checks"]["tools_list"] = True
            async def call(name, arguments):
                response = await session.call_tool(name, arguments)
                assert not response.isError, name + " failed"
                assert response.structuredContent and response.content[0].type == "text"
                return response.structuredContent
            requests = await call("list_my_requests", {"limit": 10})
            evidence["checks"]["list_my_requests"] = True
            evidence["visible_request_count"] = len(requests["items"])
            for name in ("list_review_queue", "list_tasks"):
                await call(name, {"limit": 5})
                evidence["checks"][name] = True
            if submit:
                receipt = await call("submit_request", {"text": "MCP 개발 시험: 주간 고객 문의를 분류하여 AI팀의 보고서 초안을 만들어 주세요."})
                request_id = receipt["request_id"]
                evidence["checks"]["submit_request"] = True
                evidence["request_id"] = request_id
            else:
                assert requests["items"], "No visible DB requests; use --submit for one mock request"
                request_id = requests["items"][0]["id"]
            data = await call("get_request_result", {"request_id": request_id})
            evidence["checks"]["get_request_result"] = True
            for _ in range(60 if submit else 0):
                if data["judgment"]:
                    break
                await asyncio.sleep(1)
                data = await call("get_request_result", {"request_id": request_id})
            evidence["status"] = data["status"]
            evidence["final"] = bool(data["judgment"])
            if data["judgment"]:
                judgment = data["judgment"]
                assert set(judgment["classifications"]) == {"ai_need", "feasibility", "urgency", "lead_org"}
                evidence["classification_keys"] = list(judgment["classifications"])
                evidence["confidence_output_count"] = sum("confidence" in x for x in judgment["outputs"])
                evidence["draft_task_count"] = len(judgment["draft_tasks"])
                evidence["rule_effects_present"] = "rule_effects" in judgment
            invalid = await session.call_tool("list_my_requests", {"limit": 11})
            assert invalid.isError
            evidence["checks"]["invalid_limit_rejected"] = True
    return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8787/mcp")
    parser.add_argument("--submit", action="store_true", help="새 요청 1건 생성 (AI_MODE 확인 후 실행)")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    evidence = asyncio.run(check(args.url, args.submit))
    text = json.dumps(evidence, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
