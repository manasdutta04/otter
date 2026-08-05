# veridexs CLI

The CLI is a thin terminal client for the veridexs API. It does not duplicate repository analysis logic.

## Local usage

```powershell
pip install -e apps/cli
$env:VERIDEXS_SESSION = "your_session_cookie_value"
veridexs health
veridexs analyze <repository-id>
veridexs review <repository-id>
veridexs architect <repository-id>
veridexs plan <repository-id> "Add Google OAuth"
veridexs docs <repository-id>
```

The session cookie is intentionally supplied through the environment rather than printed by the API or stored in the CLI source.
