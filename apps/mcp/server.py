import json
import os
import sys
from urllib.request import Request, urlopen


def api_call(repository_id: str) -> dict:
    url = os.getenv("VERIDEXS_API_URL", "http://localhost:8000").rstrip("/")
    request = Request(f"{url}/repositories/{repository_id}/intelligence", headers={"Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def handle(message: dict) -> dict:
    method = message.get("method")
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": message.get("id"), "result": {"tools": [{"name": "repository_intelligence", "description": "Get veridexs intelligence for a repository", "inputSchema": {"type": "object", "properties": {"repository_id": {"type": "string"}}, "required": ["repository_id"]}}]}}
    if method == "tools/call" and message.get("params", {}).get("name") == "repository_intelligence":
        repository_id = message["params"]["arguments"]["repository_id"]
        return {"jsonrpc": "2.0", "id": message.get("id"), "result": {"content": [{"type": "text", "text": json.dumps(api_call(repository_id))}]}}
    return {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": -32601, "message": "Method not found"}}


for line in sys.stdin:
    try:
        print(json.dumps(handle(json.loads(line))), flush=True)
    except Exception as error:
        print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": str(error)}}), flush=True)
