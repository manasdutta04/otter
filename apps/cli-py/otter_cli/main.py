import argparse
import json
import os
import sys
import httpx


def client(api_url: str) -> httpx.Client:
    headers = {}
    token = os.getenv("OTTER_SESSION")
    if token:
        headers["Cookie"] = f"otter_session={token}"
        headers["X-Otter-Session"] = token
    return httpx.Client(base_url=api_url.rstrip("/"), headers=headers, timeout=30)


def emit(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(prog="otter-py", description="Legacy Otter Python CLI")
    parser.add_argument("--api-url", default=os.getenv("OTTER_API_URL", "http://localhost:8000"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["health", "review", "architect", "analyze", "docs"]:
        command = sub.add_parser(name)
        if name != "health":
            command.add_argument("repository_id")
    plan = sub.add_parser("plan")
    plan.add_argument("repository_id")
    plan.add_argument("request")
    args = parser.parse_args()
    try:
        with client(args.api_url) as api:
            if args.command == "health":
                response = api.get("/health")
            elif args.command == "plan":
                response = api.post(f"/repositories/{args.repository_id}/plans", json={"request": args.request})
            elif args.command == "review":
                response = api.get(f"/repositories/{args.repository_id}/review")
            elif args.command == "architect":
                response = api.get(f"/repositories/{args.repository_id}/architecture")
            elif args.command == "analyze":
                response = api.get(f"/repositories/{args.repository_id}/intelligence")
            else:
                response = api.get(f"/repositories/{args.repository_id}/documents")
            response.raise_for_status()
            emit(response.json())
    except httpx.HTTPStatusError as error:
        print(f"Otter API error {error.response.status_code}: {error.response.text}", file=sys.stderr)
        raise SystemExit(1)
    except httpx.HTTPError as error:
        print(f"Otter connection error: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
