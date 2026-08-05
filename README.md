# veridexs
﻿# veridexs

veridexs is an engineering-intelligence platform for understanding repositories, planning changes, and improving software quality.

## Phase 1 local development

1. Copy `.env.example` to `.env`.
2. Add a GitHub OAuth App with callback URL `http://localhost:8000/auth/github/callback` and fill in the client credentials.
3. Run `docker compose -f docker/compose.yml up --build`.
4. Open [http://localhost:3000](http://localhost:3000).

The first vertical slice provides GitHub OAuth initiation, GitHub URL import, asynchronous shallow cloning, repository status, and a dashboard workspace.
