#!/usr/bin/env python3
# claude_full_stats.py - TOUTES stats CLI OAuth (quotas + analytics)
import requests
import json
from pathlib import Path
import sys
from datetime import datetime

class ClaudeStats:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        })
        self.token = self._get_token()
        self.session.headers["Authorization"] = f"Bearer {self.token}"
    
    def _get_token(self):
        creds_file = Path.home() / ".claude" / ".credentials.json"
        if not creds_file.exists():
            print("❌ Lancez 'claude login'")
            sys.exit(1)
        with open(creds_file, 'r') as f:
            return json.load(f)['claudeAiOauth']['accessToken']
    
    def usage(self, period="day"):
        """Quotas Pro/Max"""
        r = self.session.get(f"https://api.anthropic.com/api/oauth/usage?period={period}")
        return r.json() if r.ok else None
    
    def code_analytics(self):
        """Stats Claude Code (sessions, commits, etc.)"""
        r = self.session.get("https://api.anthropic.com/v1/organizations/usage_report/claude_code")
        return r.json() if r.ok else None
    
    def token_count(self, text):
        """Tokens avant envoi"""
        r = self.session.post("https://api.anthropic.com/v1/token-count", 
                             json={"model": "claude-3.5-sonnet-20240620", "text": text[:2000]})
        return r.json() if r.ok else None

# ═══════════════════════════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════════════════════════

stats = ClaudeStats()
print("\n" + "═"*80)
print("📊 TOUTES LES STATISTIQUES CLAUDE CODE (OAuth CLI)")
print("═"*80)

# 1. QUOTAS PRINCIPAUX
print("\n1️⃣ QUOTAS PRO/MAX")
daily = stats.usage("day")
weekly = stats.usage("week")
if daily:
    print(f"  Messages restants/jour: {daily.get('remaining_messages', 'N/A')}")
    print(f"  Tier: {daily.get('rate_limit_tier')}")
    print(f"  Abonnement: {daily.get('subscription_type', 'pro')}")
    print(json.dumps(daily, indent=2)[:600] + "...")

# 2. ANALYTICS CLAUDE CODE
print("\n2️⃣ ANALYTICS PRODUCTIVITÉ")
analytics = stats.code_analytics()
if analytics:
    print(f"  Sessions/jour: {analytics.get('num_sessions', 0)}")
    print(f"  Lignes ajoutées: {analytics.get('lines_of_code', {}).get('added', 0)}")
    print(json.dumps(analytics, indent=2)[:800] + "...")
else:
    print("  ℹ Nécessite clé admin OU accès workspace")

# 3. TEST TOKEN COUNT
print("\n3️⃣ COMPTEUR TOKENS")
tokens = stats.token_count("Votre message de test ici")
if tokens:
    print(f"  Tokens texte test: {tokens.get('input_tokens', 0)}")

print("\n✅ CLI Token = stats complètes (quotas + productivité)!")
