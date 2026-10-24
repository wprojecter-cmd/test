# GraphQL Request Lab

A small FastAPI + HTML learning demo for inspecting GraphQL request structure and validation-style errors.

## Safety behavior

- The app does **not** contact Render Dashboard or any external GraphQL endpoint.
- The app does **not** read, accept, or log cookies, dashboard sessions, or API keys.
- `POST /api/demo-mutation` returns a simulated GraphQL validation error for the intentionally renamed `provisionTestAPIToken` field.
- No Render API key is created.

## Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000.

## Deploy on Render

Create a **Web Service** from this repository.

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

No secret environment variables are required. Optional `GRAPHQL_DEMO_LABEL` only changes the default demonstration label and is not a credential.
