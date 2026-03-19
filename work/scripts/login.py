import undetected_chromedriver as uc
import json
import time
import os
import sys

# Patch silencieux
uc.Chrome.__del__ = lambda self: None

CONFIG_FILE = "claude_monitor_config.json"


def intercept_smart():
    options = uc.ChromeOptions()
    options.add_argument("--no-first-run --no-service-autorun --password-store=basic")
    options.add_argument("--log-level=3")

    driver = None
    try:
        # On utilise une version stable connue
        driver = uc.Chrome(options=options, version_main=143)
        driver.get("https://claude.ai/login")

        while True:
            try:
                if not driver.window_handles:
                    return
                if "claude.ai/chat" in driver.current_url or "claude.ai/new" in driver.current_url:
                    time.sleep(3)  # Pause pour laisser Cloudflare écrire ses cookies
                    break
            except Exception:
                pass
            time.sleep(1)

        # Extraction intelligente
        cookies = driver.get_cookies()

        # On cherche les 2 sésames
        session_key = next((c['value'] for c in cookies if c['name'] == 'sessionKey'), None)
        cf_clearance = next((c['value'] for c in cookies if c['name'] == 'cf_clearance'), None)

        if session_key:
            data = {"session_key": session_key}
            if cf_clearance:
                data["cf_clearance"] = cf_clearance
                print("✅ SessionKey + Cloudflare Clearance trouvés.")
            else:
                print("⚠️ SessionKey trouvée (sans clearance).")

            # Préservation org_id
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        old = json.load(f)
                        if "org_id" in old:
                            data["org_id"] = old["org_id"]
                except Exception:
                    pass

            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f)

    except Exception:
        pass
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        sys.exit(0)


if __name__ == "__main__":
    intercept_smart()
