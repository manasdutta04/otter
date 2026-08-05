import json
import httpx
from fastapi import HTTPException
from .config import get_settings

async def generate_patch(request: str, files: list[dict[str, str]]) -> dict[str, object]:
    settings = get_settings()
    if not settings.llm_api_key:
        raise HTTPException(status_code=503, detail="LLM patch generation is not configured")
    context = "\n\n".join(f"FILE: {item['path']}\n{item['content'][:12000]}" for item in files[:20])
    prompt = f"Return only valid JSON with keys summary and files. files must be an array of objects with path and complete content. Do not include markdown fences. Requested change: {request}\nRepository context:\n{context}"
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(f"{settings.llm_base_url.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {settings.llm_api_key}"}, json={"model": settings.llm_model, "temperature": 0.1, "messages": [{"role": "system", "content": "You are a cautious senior software engineer. Produce minimal, reviewable patches and never invent files without need."}, {"role": "user", "content": prompt}]})
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    try:
        result = json.loads(content)
        if not isinstance(result.get("files"), list) or not result.get("summary"):
            raise ValueError("Invalid patch shape")
        return result
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail="LLM returned an invalid patch proposal") from error
