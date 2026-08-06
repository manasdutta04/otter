import json
import os
import sys
from urllib.request import Request, urlopen


def api_call(path: str, payload: dict | None = None) -> dict:
    url = os.getenv("VERIDEXS_API_URL", "http://localhost:8000").rstrip("/")
    session = os.getenv("VERIDEXS_SESSION")
    headers = {"Accept": "application/json"}
    if session:
        headers["Cookie"] = f"veridexs_session={session}"
    
    body = json.dumps(payload).encode("utf-8") if payload else None
    if body:
        headers["Content-Type"] = "application/json"

    request = Request(f"{url}{path}", data=body, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read())

def handle(message: dict) -> dict:
    method = message.get("method")
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "repository_intelligence",
                        "description": "Get veridexs intelligence for a repository",
                        "inputSchema": {"type": "object", "properties": {"repository_id": {"type": "string"}}, "required": ["repository_id"]}
                    },
                    {
                        "name": "repository_chat",
                        "description": "Ask grounded semantic questions about repository code",
                        "inputSchema": {"type": "object", "properties": {"repository_id": {"type": "string"}, "question": {"type": "string"}}, "required": ["repository_id", "question"]}
                    },
                    {
                        "name": "repository_plan",
                        "description": "Generate implementation plan for feature change",
                        "inputSchema": {"type": "object", "properties": {"repository_id": {"type": "string"}, "request": {"type": "string"}}, "required": ["repository_id", "request"]}
                    },
                    {
                        "name": "repository_review",
                        "description": "Get code review and health analysis for repository",
                        "inputSchema": {"type": "object", "properties": {"repository_id": {"type": "string"}}, "required": ["repository_id"]}
                    }
                ]
            }
        }
    if method == "tools/call":
        params = message.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        repo_id = args.get("repository_id")

        if tool_name == "repository_intelligence":
            res = api_call(f"/repositories/{repo_id}/intelligence")
        elif tool_name == "repository_chat":
            res = api_call(f"/repositories/{repo_id}/chat", {"question": args.get("question")})
        elif tool_name == "repository_plan":
            res = api_call(f"/repositories/{repo_id}/plans", {"request": args.get("request")})
        elif tool_name == "repository_review":
            res = api_call(f"/repositories/{repo_id}/review")
        else:
            return {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": -32601, "message": f"Tool {tool_name} not found"}}

        return {"jsonrpc": "2.0", "id": message.get("id"), "result": {"content": [{"type": "text", "text": json.dumps(res)}]}}

    return {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": -32601, "message": "Method not found"}}


for line in sys.stdin:
    try:
        print(json.dumps(handle(json.loads(line))), flush=True)
    except Exception as error:
        print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": str(error)}}), flush=True)
