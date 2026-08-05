import hashlib
import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="veridexs GitHub App")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/github")
async def github_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None)) -> dict[str, str]:
    body = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if secret:
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not x_hub_signature_256 or not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    event = request.headers.get("x-github-event", "unknown")
    return {"status": "accepted", "event": event}
