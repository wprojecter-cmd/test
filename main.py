import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEMO_LABEL = os.getenv("GRAPHQL_DEMO_LABEL", "WorldGame-Test")

app = FastAPI(title="GraphQL Request Lab", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class DemoRequest(BaseModel):
    label: str = Field(default="WorldGame-Test", min_length=1, max_length=80)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "local-demo-only"}


@app.post("/api/demo-mutation")
async def demo_mutation(body: DemoRequest) -> dict[str, Any]:
    """
    Demonstration only. This endpoint does not make any outbound HTTP requests.
    It shows a GraphQL-shaped request and simulates the schema validation error
    expected for an unknown mutation field.
    """
    label = body.label.strip() or DEMO_LABEL
    payload = {
        "operationName": "ProvisionTestAPIToken",
        "query": (
            "mutation provisionTestAPIToken($labelTest: String) {\n"
            "  provisionTestAPIToken(labelTest: $labelTest) {\n"
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
        "variables": {"labelTest": label},
    }

    return {
        "mode": "simulated-validation-error",
        "sent_to_external_server": False,
        "created_api_key": False,
        "request": payload,
        "response": {
            "errors": [
                {
                    "message": (
                        "Cannot query field 'provisionTestAPIToken' on type "
                        "'Mutation'. This is a simulated local demo error; "
                        "no external GraphQL server was contacted."
                    ),
                    "extensions": {"code": "GRAPHQL_VALIDATION_FAILED"},
                }
            ]
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
