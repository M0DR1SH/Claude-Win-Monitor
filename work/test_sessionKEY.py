"""
Script : detect_claude_session.py

Version anti-détection : masque Playwright pour passer les protections Claude.ai.
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


TARGET_COOKIES = {"sessionKey", "lastActiveOrg"}
PROFILE_DIR = str(Path("playwright-claude-profile").absolute())


def check_session():
    """Vérifie si une session Claude existe déjà dans le profil Playwright."""
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
        )
        cookies = context.cookies(["https://claude.ai"])
        context.close()

        found = {c["name"]: c["value"] for c in cookies if c["name"] in TARGET_COOKIES}
        return found


def create_or_update_profile():
    """Ouvre une fenêtre Playwright Chromium masqué pour se connecter à Claude."""
    print("Ouverture du profil Playwright Chromium (mode anti-détection)...")
    print("1) Connectez-vous à Claude.ai via Google")
    print("2) Fermez la fenêtre quand c'est fait")
    print("3) Relancez ce script pour utiliser la session.")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="fr-FR",
            timezone_id="Europe/Paris",
            permissions=["geolocation"],
        )

        # Anti-détection navigateur
        context.add_init_script("""
            // Masquer webdriver et autres signaux bot
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR', 'fr', 'en-US']});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({ query: () => Promise.resolve({ state: 'granted' }) })
            });
        """)

        page = context.new_page()
        page.goto("https://claude.ai", wait_until="networkidle")
        input("\nAppuyez sur Entrée quand vous êtes connecté...")
        context.close()


def main():
    print("=== Détection session Claude via Playwright (anti-détection) ===")

    # Vérifier si session déjà présente
    session = check_session()
    if session:
        print("\n✅ Session trouvée :")
        for k, v in session.items():
            print(f"{k} = {v}")
        return

    # Pas de session → créer/mettre à jour
    print("\n❌ Aucune session trouvée.")
    create_or_update_profile()


if __name__ == "__main__":
    main()
