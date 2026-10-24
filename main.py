import asyncio
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Intentionally invalid demo credential. Never replace it with a real key here.
DEMO_BEARER_TOKEN = "Hello World!"
RENDER_SAFE_TEST_URL = "https://api.render.com/v1/services?limit=1"

app = FastAPI(title="GraphQL Request Lab", version="1.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class DemoRequest(BaseModel):
    label: str = Field(default="WorldGame-Test", min_length=1, max_length=80)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "safe-live-http-test"}


def perform_safe_render_request() -> dict[str, Any]:
    """Make a read-only request to Render's public REST API with a fake credential."""
    req = urllib.request.Request(
        RENDER_SAFE_TEST_URL,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {DEMO_BEARER_TOKEN}",
            "User-Agent": "GraphQL-Request-Lab-Demo/1.1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            raw = response.read(12000).decode("utf-8", errors="replace")
            return {
                "http_status": response.status,
                "headers": {
                    "content_type": response.headers.get("Content-Type", ""),
                    "request_id": response.headers.get("x-request-id", ""),
                },
                "body": raw,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read(12000).decode("utf-8", errors="replace")
        return {
            "http_status": exc.code,
            "headers": {
                "content_type": exc.headers.get("Content-Type", ""),
                "request_id": exc.headers.get("x-request-id", ""),
            },
            "body": raw,
        }
    except Exception as exc:
        return {
            "http_status": None,
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
        }


@app.post("/api/demo-mutation")
async def demo_mutation(body: DemoRequest) -> dict[str, Any]:
    """
    Keep the GraphQL-shaped mutation as a display-only REQUEST.
    The only outbound call is a read-only GET to Render's documented public
    REST API using an intentionally invalid placeholder bearer value.
    No Dashboard cookies/session data are used and no key-creation mutation
    is sent or executed.
    """
    label = body.label.strip() or "WorldGame-Test"
    request_object = {
        "operationName": "ProvisionTestAPIToken",
        "query": (
            "mutation provisionTestAPIToken($labelTest: String) {\\n"
            "  provisionTestAPIToken(labelTest: $labelTest) {\\n"
            "    id\\n"
            "    createdAt\\n"
            "    label\\n"
            "    lastUsedAt\\n"
            "    token\\n"
            "    expiresAt\\n"
            "    type\\n"
            "    __typename\\n"
            "  }\\n"
            "}"
        ),
        "variables": {"labelTest": label},
    }

    # This REQUEST is for inspection only; it is deliberately never transmitted.
    request_json = json.dumps(request_object, ensure_ascii=False)
    live_response = await asyncio.to_thread(perform_safe_render_request)

    return {
        "mode": "safe-live-http-test",
        "sent_to_render": True,
        "target": RENDER_SAFE_TEST_URL,
        "method": "GET",
        "sent_graphql_mutation": False,
        "created_api_key": False,
        "request": request_object,
        "request_json_length": len(request_json),
        "live_response": live_response,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
