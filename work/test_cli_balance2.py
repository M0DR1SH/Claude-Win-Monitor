#!/usr/bin/env python3
import requests, json
from pathlib import Path

creds_file = Path.home() / ".claude" / ".credentials.json"
with open(creds_file) as f:
    cli_token = json.load(f)["claudeAiOauth"]["accessToken"]

headers = {
    "Authorization": f"Bearer {cli_token}",
    "anthropic-beta": "oauth-2025-04-20",
    "User-Agent": "claude-code/2.1.5",
}

BASE = "https://api.anthropic.com"

for path in ["/api/oauth/account", "/api/oauth/profile"]:
    r = requests.get(BASE + path, headers=headers, timeout=8)
    print(f"\n{'='*60}")
    print(f"[{r.status_code}] {path}")
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
