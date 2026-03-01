#!/usr/bin/env python3
# test_cli_balance.py - Cherche l'endpoint du solde prepaid sur api.anthropic.com
import requests
import json
from pathlib import Path

creds_file = Path.home() / ".claude" / ".credentials.json"
with open(creds_file) as f:
    cli_token = json.load(f)["claudeAiOauth"]["accessToken"]

headers = {
    "Authorization": f"Bearer {cli_token}",
    "anthropic-beta": "oauth-2025-04-20",
    "User-Agent": "claude-code/2.1.5",
    "Content-Type": "application/json",
}

BASE = "https://api.anthropic.com"

candidates = [
    "/api/oauth/usage",           # connu OK
    "/api/oauth/credits",
    "/api/oauth/balance",
    "/api/oauth/billing",
    "/api/oauth/prepaid",
    "/api/oauth/account",
    "/api/oauth/profile",
    "/api/oauth/organizations",
    "/v1/usage",
    "/v1/billing",
    "/v1/balance",
    "/api/billing",
    "/api/balance",
    "/api/credits",
    "/api/account",
    "/api/profile",
    "/api/organizations",
    "/api/user",
    "/api/me",
]

print(f"Token CLI : {cli_token[:25]}...")
print("="*60)

for path in candidates:
    url = BASE + path
    try:
        r = requests.get(url, headers=headers, timeout=8)
        status = r.status_code
        if status == 200:
            data = r.json()
            print(f"[200] {path}")
            print(f"      => {json.dumps(data)[:200]}")
        elif status == 401:
            print(f"[401] {path}  (token refusé)")
        elif status == 403:
            print(f"[403] {path}  (interdit)")
        elif status == 404:
            print(f"[404] {path}  (inexistant)")
        else:
            print(f"[{status}] {path}")
    except Exception as e:
        print(f"[ERR] {path} -> {e}")
