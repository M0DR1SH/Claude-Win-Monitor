#!/usr/bin/env python3
# test_cli_on_claudeai.py - Test si le token CLI fonctionne sur les endpoints claude.ai
import requests
import json
from pathlib import Path

# Charger le token CLI
creds_file = Path.home() / ".claude" / ".credentials.json"
with open(creds_file) as f:
    cli_token = json.load(f)["claudeAiOauth"]["accessToken"]

print(f"Token CLI : {cli_token[:30]}...{cli_token[-10:]}")
print("="*70)

BASE = "https://claude.ai/api"

# Headers à tester
variants = [
    {
        "label": "Bearer + anthropic-beta (style CLI)",
        "headers": {
            "Authorization": f"Bearer {cli_token}",
            "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": "claude-code/2.1.5",
            "Content-Type": "application/json",
        }
    },
    {
        "label": "Bearer seul",
        "headers": {
            "Authorization": f"Bearer {cli_token}",
            "Content-Type": "application/json",
        }
    },
    {
        "label": "Cookie sessionKey (avec CLI token)",
        "headers": {
            "Cookie": f"sessionKey={cli_token}",
            "Content-Type": "application/json",
        }
    },
]

# Etape 1 : bootstrap pour obtenir org_id
print("\n[1] Test /api/bootstrap")
for v in variants:
    try:
        r = requests.get(f"{BASE}/bootstrap", headers=v["headers"], timeout=10)
        print(f"  {v['label'][:40]:40s} -> {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            orgs = data.get("account", {}).get("memberships", [])
            if orgs:
                org_id = orgs[0]["organization"]["uuid"]
                print(f"    => org_id trouvé : {org_id}")
                v["org_id"] = org_id
    except Exception as e:
        print(f"  {v['label'][:40]:40s} -> ERREUR: {e}")

# Etape 2 : endpoints usage avec org_id si disponible
print("\n[2] Test /api/organizations/{org_id}/usage")
for v in variants:
    org_id = v.get("org_id")
    if not org_id:
        print(f"  {v['label'][:40]:40s} -> (pas d'org_id, bootstrap échoué)")
        continue
    try:
        r = requests.get(f"{BASE}/organizations/{org_id}/usage", headers=v["headers"], timeout=10)
        print(f"  {v['label'][:40]:40s} -> {r.status_code}")
        if r.status_code == 200:
            print(f"    => {json.dumps(r.json(), indent=6)[:300]}")
    except Exception as e:
        print(f"  {v['label'][:40]:40s} -> ERREUR: {e}")

# Etape 3 : endpoint /api/account (plus simple, sans org_id)
print("\n[3] Test /api/account")
for v in variants:
    try:
        r = requests.get(f"{BASE}/account", headers=v["headers"], timeout=10)
        print(f"  {v['label'][:40]:40s} -> {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"    => {list(data.keys())}")
    except Exception as e:
        print(f"  {v['label'][:40]:40s} -> ERREUR: {e}")

# Etape 4 : endpoint oauth/usage sur api.anthropic.com (référence - connu OK)
print("\n[4] Référence : api.anthropic.com/api/oauth/usage (connu OK)")
r = requests.get(
    "https://api.anthropic.com/api/oauth/usage",
    headers={
        "Authorization": f"Bearer {cli_token}",
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "claude-code/2.1.5",
    },
    timeout=10
)
print(f"  -> {r.status_code}")
if r.status_code == 200:
    print(f"  => {json.dumps(r.json(), indent=4)}")
