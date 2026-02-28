#!/usr/bin/env python3
# test_cookie_auto.py - Lecture automatique du cookie sessionKey depuis Chrome/Edge
import os
import json
import base64
import sqlite3
import shutil
import tempfile
from pathlib import Path

# Windows DPAPI + AES-GCM
try:
    import win32crypt
    from Crypto.Cipher import AES
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    print("Dependances manquantes. Installation:")
    print("  pip install pywin32 pycryptodome")
    exit(1)


def get_encryption_key(browser_path):
    """Lit et dechiffre la cle AES depuis Local State (DPAPI)."""
    local_state_path = browser_path / "Local State"
    if not local_state_path.exists():
        return None
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    encrypted_key = base64.b64decode(
        local_state["os_crypt"]["encrypted_key"]
    )
    # Supprimer le prefixe "DPAPI"
    encrypted_key = encrypted_key[5:]
    key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return key


def decrypt_cookie(encrypted_value, key):
    """Dechiffre un cookie AES-GCM (format Chrome v80+)."""
    try:
        # Format : b'v10' + nonce(12) + ciphertext + tag(16)
        if encrypted_value[:3] == b'v10':
            nonce = encrypted_value[3:15]
            ciphertext = encrypted_value[15:]
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext[:-16], ciphertext[-16:]).decode("utf-8")
    except Exception:
        pass
    # Fallback DPAPI (ancien format)
    try:
        return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode("utf-8")
    except Exception:
        pass
    return None


def find_session_key(browser_name, browser_path):
    """Cherche le cookie sessionKey de claude.ai dans un navigateur."""
    cookies_path = browser_path / "Default" / "Network" / "Cookies"
    if not cookies_path.exists():
        cookies_path = browser_path / "Default" / "Cookies"
    if not cookies_path.exists():
        print(f"  [{browser_name}] Base cookies introuvable")
        return None

    key = get_encryption_key(browser_path)
    if not key:
        print(f"  [{browser_name}] Cle de chiffrement introuvable")
        return None

    # Ouverture directe sans verrou (immutable=1 contourne le lock Chrome)
    import urllib.parse
    cookies_uri = "file:" + urllib.parse.quote(str(cookies_path).replace("\\", "/")) + "?mode=ro&immutable=1"

    try:
        conn = sqlite3.connect(cookies_uri, uri=True)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, encrypted_value
            FROM cookies
            WHERE host_key LIKE '%claude.ai%'
              AND name = 'sessionKey'
        """)
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"  [{browser_name}] Erreur lecture SQLite : {e}")
        return None

    if not rows:
        print(f"  [{browser_name}] Aucun cookie sessionKey pour claude.ai")
        return None

    for name, encrypted_value in rows:
        value = decrypt_cookie(encrypted_value, key)
        if value:
            print(f"  [{browser_name}] sessionKey trouve : {value[:30]}...{value[-10:]}")
            return value
        else:
            print(f"  [{browser_name}] Dechiffrement echoue")
    return None


def validate_session_key(session_key):
    """Verifie que la sessionKey fonctionne sur l'API claude.ai."""
    import requests
    headers = {
        "Cookie": f"sessionKey={session_key}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.get("https://claude.ai/api/bootstrap", headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            account = data.get("account", {})
            name = account.get("full_name", "?")
            email = account.get("email_address", "?")
            orgs = account.get("memberships", [])
            org_id = orgs[0]["organization"]["uuid"] if orgs else "?"
            print(f"\n  Validation OK !")
            print(f"  Nom    : {name}")
            print(f"  Email  : {email}")
            print(f"  org_id : {org_id}")
            return True
        else:
            print(f"\n  Validation echouee : HTTP {r.status_code}")
    except Exception as e:
        print(f"\n  Erreur validation : {e}")
    return False


# ─── MAIN ───────────────────────────────────────────────────────────────────

APP_DATA = Path(os.environ.get("LOCALAPPDATA", ""))

BROWSERS = {
    "Chrome":   APP_DATA / "Google"        / "Chrome"         / "User Data",
    "Edge":     APP_DATA / "Microsoft"     / "Edge"           / "User Data",
    "Brave":    APP_DATA / "BraveSoftware" / "Brave-Browser"  / "User Data",
    "Chromium": APP_DATA / "Chromium"      / "User Data",
}

print("="*60)
print("Recherche automatique du cookie sessionKey claude.ai")
print("="*60)

found_key = None
for browser_name, browser_path in BROWSERS.items():
    if not browser_path.exists():
        print(f"  [{browser_name}] Non installe")
        continue
    key = find_session_key(browser_name, browser_path)
    if key and not found_key:
        found_key = key

if found_key:
    print("\n" + "="*60)
    print("Test de la sessionKey sur claude.ai...")
    validate_session_key(found_key)
else:
    print("\nAucune sessionKey trouvee dans les navigateurs.")
    print("=> L'utilisateur doit se connecter sur claude.ai dans son navigateur.")
