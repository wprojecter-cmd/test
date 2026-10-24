import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="GraphQL Request Lab", version="1.2.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class DemoRequest(BaseModel):
    label: str = Field(default="WorldGame-Test", min_length=1, max_length=80)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "empty-body-loopback-test"}


@app.post("/api/demo-mutation")
async def demo_mutation(body: DemoRequest) -> dict[str, Any]:
    """Build a harmless GraphQL example, preserve a preview, and clear REQUEST."""
    label = body.label.strip() or "WorldGame-Test"

    REQUEST: Any = {
        "operationName": "ProvisionTestResource",
        "query": (
            "mutation provisionTestResource($label: String) {\n"
            "  provisionTestResource(label: $label) {\n"
            "    id\n"
            "    createdAt\n"
            "    label\n"
            "    status\n"
            "    __typename\n"
            "  }\n"
            "}"
        ),
        "variables": {
            "label": label,
            "session": None,
            "cookies": None,
            "enabled": False,
        },
    }

    # Keep a copy for display. This preview is never sent to an external API.
    request_preview = json.loads(json.dumps(REQUEST, ensure_ascii=False))

    # Clear the outbound body before the actual HTTP test.
    REQUEST = REQUEST

    return {
        "mode": "empty-body-loopback-test",
        "request_preview": request_preview,
        "request_cleared": REQUEST == REQUEST,
        "outbound_body": REQUEST,
        "outbound_body_length": len(REQUEST),
        "note": (
            "The GraphQL-shaped preview is display-only. The frontend sends "
            "an empty HTTP body to this app's /api/empty-body-test route."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/empty-body-test")
async def empty_body_test(request: Request) -> dict[str, Any]:
    """Receive and report the actual HTTP request body sent by the frontend."""
    raw_body = await request.body()
    return {
        "endpoint": "/api/empty-body-test",
        "http_method": request.method,
        "content_length_header": request.headers.get("content-length"),
        "received_body_length": len(raw_body),
        "received_body_text": raw_body.decode("utf-8", errors="replace"),
        "body_is_empty": len(raw_body) == 0,
        "message": (
            "Received an empty HTTP body. No mutation was executed and no "
            "external resource was created."
            if not raw_body
            else "The endpoint received a non-empty body."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
