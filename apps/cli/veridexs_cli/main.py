import argparse
import json
import os
import sys
import httpx

def client(api_url: str) -> httpx.Client:
    headers = {}
    token = os.getenv("VERIDEXS_SESSION")
    if token:
        headers["Cookie"] = f"veridexs_session={token}"
    return httpx.Client(base_url=api_url.rstrip("/"), headers=headers, timeout=30)

def emit(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))

def main() -> None:
    parser = argparse.ArgumentParser(prog="veridexs", description="Engineering intelligence from your terminal")
    parser.add_argument("--api-url", default=os.getenv("VERIDEXS_API_URL", "http://localhost:8000"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["health", "review", "architect", "analyze", "docs"]:
        command = sub.add_parser(name)
        command.add_argument("repository_id")
    plan = sub.add_parser("plan")
    plan.add_argument("repository_id")
    plan.add_argument("request")
    args = parser.parse_args()
    paths = {"health": "/health", "review": f"/repositories/{args.repository_id}/review", "architect": f"/repositories/{args.repository_id}/architecture", "analyze": f"/repositories/{args.repository_id}/intelligence", "docs": f"/repositories/{args.repository_id}/documents"}
    try:
        with client(args.api_url) as api:
            if args.command == "health": response = api.get(paths[args.command])
            elif args.command == "plan": response = api.post(f"/repositories/{args.repository_id}/plans", json={"request": args.request})
            else: response = api.get(paths[args.command])
            response.raise_for_status()
            emit(response.json())
    except httpx.HTTPStatusError as error:
        print(f"veridexs API error {error.response.status_code}: {error.response.text}", file=sys.stderr); raise SystemExit(1)
    except httpx.HTTPError as error:
        print(f"veridexs connection error: {error}", file=sys.stderr); raise SystemExit(1)
