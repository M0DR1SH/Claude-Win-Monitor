#!/usr/bin/env python3
# claude_usage_display.py - Affiche stats avec sessionKey CLI ET Browser
import requests
import json
from pathlib import Path
import subprocess
import sys

# ═══════════════════════════════════════════════════════════════
# 1. EXTRACTION TOKENS AUTOMATIQUE
# ═══════════════════════════════════════════════════════════════

def get_cli_token():
    """OAuth depuis Claude Code"""
    creds_file = Path.home() / ".claude" / ".credentials.json"
    if creds_file.exists():
        with open(creds_file, 'r') as f:
            oauth = json.load(f)['claudeAiOauth']
        return oauth['accessToken']
    return None

def get_browser_token():
    """TODO: Auto depuis Chrome/Edge (manuel pour l'instant)"""
    print("💡 Browser: Copiez manuellement depuis DevTools claude.ai")
    return input("Collez sessionKey (sk-ant-sid...): ").strip()

# Tokens
cli_token = get_cli_token()
browser_token = get_browser_token() if not cli_token else None

if not cli_token and not browser_token:
    print("❌ Aucun token trouvé. Lancez 'claude login'")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# 2. REQUÊTE API USAGE
# ═══════════════════════════════════════════════════════════════

def fetch_usage(token, label):
    headers = {
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "claude-code/2.1.5",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get("https://api.anthropic.com/api/oauth/usage?period=day", 
                          headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n✅ {label} OK")
            print(json.dumps(data, indent=2)[:800] + "..." if len(str(data)) > 800 else json.dumps(data, indent=2))
            return True
        else:
            print(f"❌ {label} échoué: {resp.status_code}")
    except Exception as e:
        print(f"❌ {label} erreur: {e}")
    return False

# Tests
print("\n" + "="*70)
print("📊 STATS USAGE CLAUDE (CLI vs Browser)")
print("="*70)

if cli_token:
    print(f"🔧 CLI Token : {cli_token[:40]}...")
    fetch_usage(cli_token, "CLI OAuth")

if browser_token:
    print(f"\n🌐 Browser Token: {browser_token[:40]}...")
    fetch_usage(browser_token, "Browser sessionKey")

print("\n🎯 Résultats identiques = parfait pour tracker!")
