#!/usr/bin/env python3
# test_cookie_browser3.py - Lecture cookie via browser_cookie3
import browser_cookie3
import requests

DOMAIN = "claude.ai"
COOKIE_NAME = "sessionKey"

def find_session_key():
    browsers = [
        ("Chrome", browser_cookie3.chrome),
        ("Edge",   browser_cookie3.edge),
        ("Brave",  browser_cookie3.brave),
    ]
    for name, loader in browsers:
        try:
            jar = loader(domain_name=DOMAIN)
            for cookie in jar:
                if cookie.name == COOKIE_NAME:
                    print(f"[{name}] sessionKey trouve : {cookie.value[:30]}...{cookie.value[-10:]}")
                    return cookie.value
            print(f"[{name}] Aucun cookie sessionKey pour {DOMAIN}")
        except Exception as e:
            print(f"[{name}] Erreur : {e}")
    return None

def validate(session_key):
    r = requests.get(
        "https://claude.ai/api/bootstrap",
        headers={"Cookie": f"sessionKey={session_key}"},
        timeout=10
    )
    if r.status_code == 200:
        acc = r.json().get("account", {})
        print(f"\nValidation OK !")
        print(f"  Nom    : {acc.get('full_name')}")
        print(f"  Email  : {acc.get('email_address')}")
        orgs = acc.get("memberships", [])
        if orgs:
            print(f"  org_id : {orgs[0]['organization']['uuid']}")
    else:
        print(f"\nValidation echouee : HTTP {r.status_code}")

print("="*60)
print("Recherche sessionKey claude.ai via browser_cookie3")
print("="*60)

key = find_session_key()
if key:
    validate(key)
else:
    print("\nAucune sessionKey trouvee.")
