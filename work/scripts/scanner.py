from curl_cffi import requests

# --- CONFIGURATION ---
BASE_URL = "https://claude.ai/api"
SESSION_KEY = (
    "sk-ant-sid01-7LuUA5dBHbnMIrN1gsSbxXXEybbM84OUHpTY4cnyUcwJN13sITNYf6Efb1"
    "I2UjyQ996SZb3WvRQGSZ29O3jP8Q-hwcHlwAA"
)
# Votre ID d'organisation PRO
ORG_ID = "d637f37f-43f8-4067-8473-59a5baa18b6a"


def run_scan():
    print("--- CLAUDE-WIN-MONITOR : PHASE 0 - SCANNER v6 (BRUTE FORCE) ---")

    headers = {
        "Cookie": f"sessionKey={SESSION_KEY}",
        "Origin": "https://claude.ai",
        "Referer": "https://claude.ai/chats",
        "Content-Type": "application/json"
    }

    session = requests.Session(impersonate="chrome120")
    session.headers.update(headers)

    # 1. D'abord, on récupère l'ID Utilisateur (User UUID) depuis le bootstrap
    print("\n1. Récupération ID Utilisateur...")
    user_id = None
    try:
        res = session.get(f"{BASE_URL}/bootstrap", timeout=10)
        data = res.json()
        user_id = data.get("account", {}).get("uuid")
        print(f"   👉 User UUID trouvé : {user_id}")
    except Exception:
        print("   ❌ Impossible de trouver l'User UUID")

    # 2. Liste des cibles potentielles
    # On teste toutes les variantes possibles
    endpoints = [
        # Variantes Billing / Usage
        f"/organizations/{ORG_ID}/billing/usage",
        f"/organizations/{ORG_ID}/billing/invoices",
        f"/organizations/{ORG_ID}/usage",
        f"/organizations/{ORG_ID}/purchases",

        # Variantes Utilisateur
        f"/users/{user_id}/usage_limits" if user_id else None,
        f"/organizations/{ORG_ID}/users/{user_id}/limits" if user_id else None,
        "/users/me/organization_memberships",

        # Variantes Modèles & Caps (Parfois les limites sont ici)
        f"/organizations/{ORG_ID}/models",
        f"/organizations/{ORG_ID}/capabilities",
        f"/organizations/{ORG_ID}/feature_flags",

        # Endpoints "cachés" parfois utilisés par le frontend
        f"/organizations/{ORG_ID}/analytics_stats",
        f"/organizations/{ORG_ID}/warnings",
    ]

    print(f"\n2. Lancement du Brute Force sur {len([e for e in endpoints if e])} endpoints...")

    found_something = False

    for path in endpoints:
        if not path:
            continue

        url = f"{BASE_URL}{path}"
        try:
            res = session.get(url, timeout=5)
            status = res.status_code

            if status == 200:
                print(f"   ✅ [200 OK] {path}")
                found_something = True

                # On regarde vite fait si y'a des mots clés
                text = res.text
                if "limit" in text or "quota" in text or "remaining" in text or "usage" in text:
                    print("      🎉 CONTIENT DES DONNÉES CLÉS ! (limit/quota/remaining)")
                    print(f"      Aperçu: {text[:300]}...")
                else:
                    print("      (JSON valide mais pas de mots-clés évidents)")
            elif status == 403:
                print(f"   🔒 [403] {path} (Interdit)")
            elif status == 404:
                # On n'affiche pas les 404 pour ne pas polluer, sauf si demandé
                # print(f"   ❌ [404] {path}")
                pass
            else:
                print(f"   ⚠️ [{status}] {path}")

        except Exception:
            pass

    if not found_something:
        print("\n❌ RÉSULTAT : Aucun endpoint secret n'a répondu.")
        print("Conclusion : Anthropic ne fournit plus ces données via API REST pour les comptes Pro.")
    else:
        print("\n✅ RÉSULTAT : Nous avons trouvé une porte d'entrée !")

    print("\n--- SCAN v6 TERMINÉ ---")


if __name__ == "__main__":
    run_scan()
