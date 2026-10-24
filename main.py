
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="GraphQL Request Lab", version="1.4.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

RENDER_GRAPHQL_URL = "https://api.render.com/graphql"
session = os.getenv("session")
cookie = os.getenv("cookie")

class DemoRequest(BaseModel):
    label: str = Field(default="test", min_length=1, max_length=80)


def make_graphql_payload(label: str) -> dict[str, Any]:
    return {
        "operationName": "provisionAPIToken",
        "query": (
            "mutation provisionAPIToken($label: String) {\n"
            "  provisionAPIToken(label: $label) {\n"
            "    id\n"
            "    createdAt\n"
            "    label\n"
            "    lastUsedAt\n"
            "    token\n"
            "    expiresAt\n"
            "    type\n"
            "    __typename\n"
            "  }\n"
            "}"
        ),
        "variables": {"label": label},
    }


def summarize_response(raw: bytes) -> dict[str, Any]:
    """Return response diagnostics without exposing token values."""
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "format": "non-json",
            "body_length": len(raw),
        }

    summary: dict[str, Any] = {
        "format": "json",
    }

    if isinstance(data, dict):
        if isinstance(data.get("errors"), list):
            summary["errors"] = [
                {
                    "message": str(item.get("message", "GraphQL error"))[:500]
                }
                for item in data["errors"][:5]
                if isinstance(item, dict)
            ]

        result_data = data.get("data")
        if isinstance(result_data, dict):
            # Report field names only, never return token values.
            summary["data_fields"] = list(result_data.keys())

        if "data" not in data and "errors" not in data:
            summary["response_keys"] = list(data.keys())[:20]

    return summary


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "render-graphql-probe"}


@app.post("/api/demo-mutation")
async def demo_mutation(body: DemoRequest) -> dict[str, Any]:
    label = body.label.strip() or "test"
    preview = make_graphql_payload(label)

    return {
        "mode": "preview-only",
        "request_preview": preview,
        "note": "This route only prepares the payload; it does not send it.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/render-graphql-test")
async def render_graphql_test(body: DemoRequest) -> dict[str, Any]:
    """
    Send the captured GraphQL operation to Render with deliberately
    invalid authentication. No real credentials or cookies are used.
    """
    label = body.label.strip() or "test"
    payload = make_graphql_payload(label)

    request_body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        RENDER_GRAPHQL_URL,
        data=request_body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer INVALID_TEST_TOKEN_DO_NOT_USE",
            "User-Agent": "GraphQL-Request-Lab/1.4",
        },
    )

    status_code: int
    response_bytes: bytes

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            status_code = response.status
            response_bytes = response.read(65536)

    except urllib.error.HTTPError as exc:
        status_code = exc.code
        response_bytes = exc.read(65536)

    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return {
            "endpoint": RENDER_GRAPHQL_URL,
            "request_sent": False,
            "error": str(reason)[:500],
            "note": (
                "The connection failed before an HTTP response was received. "
                "No real credentials were sent."
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "endpoint": RENDER_GRAPHQL_URL,
        "method": "POST",
        "operationName": payload["operationName"],
        "request_sent": True,
        "authentication": "deliberately-invalid-test-token",
        "http_status": status_code,
        "response_summary": summarize_response(response_bytes),
        "note": (
            "The request used fake authentication and sent no cookies. "
            "A rejection confirms an HTTP response from this endpoint, "
            "not that the mutation is accepted with valid authentication."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/empty-body-test")
async def empty_body_test(request: Request) -> dict[str, Any]:
    raw_body = await request.body()

    return {
        "endpoint": "/api/empty-body-test",
        "http_method": request.method,
        "received_body_length": len(raw_body),
        "body_is_empty": len(raw_body) == 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
