#!/usr/bin/env python3
# claude_creds_full.py - Extrait TOUS tokens (web + CLI)

import json
import os
import subprocess
import requests
from pathlib import Path
import re

def get_web_sessionkey():
    """Méthode manuelle: Copiez depuis DevTools"""
    print("📋 Copiez MANUELLEMENT sessionKey depuis claude.ai DevTools")
    session_key = input("Collez sessionKey (sk-ant-sid02-...): ").strip()
    return session_key

def get_web_org():
    last_org = input("Collez lastActiveOrg UUID: ").strip()
    return last_org

def get_cli_oauth():
    creds_file = Path.home() / ".claude" / ".credentials.json"
    if creds_file.exists():
        with open(creds_file, 'r') as f:
            data = json.load(f)
        oauth = data['claudeAiOauth']
        return oauth['accessToken'], oauth.get('organizationId')
    return None, None

# Extraction
print("1️⃣ WEB (claude.ai cookies)")
session_key_web = get_web_sessionkey()
org_web = get_web_org()

print("\n2️⃣ CLI (Claude Code)")
session_key_cli, org_cli = get_cli_oauth()

# Test API (optionnel)
def test_token(token, is_oauth=False):
    url = "https://api.anthropic.com/api/oauth/usage" if is_oauth else "https://claude.ai/api/usage"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        return r.status_code == 200
    except:
        return False

print("\n" + "═"*80)
print("🎯 TOKENS CLAUDE DISPONIBLES")
print("═"*80)
print(f"🌐 WEB SessionKey : {session_key_web[:30]}...")
print(f"🌐 WEB Org       : {org_web}")
print(f"💻 CLI OAuth     : {session_key_cli[:30] if session_key_cli else '❌'}...")
print(f"💻 CLI Org       : {org_cli or 'N/A'}")
print("═"*80)

print("\n✅ Utilisez WEB sessionKey pour tracker comme Claude-Usage-Tracker macOS !")
