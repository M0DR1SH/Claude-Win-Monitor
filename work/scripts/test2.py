from pathlib import Path
import shutil
import sqlite3
import os

src = Path(r"C:\Users\souli\AppData\Local\Packages\TheBrowserCompany.Arc_ttt1ap7aakyb4\LocalCache\Local\Arc\User Data\Profile 2\Network\Cookies")

print("Chemin source :", src)
print("Existe ?      :", src.exists())
print("Est un fichier:", src.is_file())

if not src.is_file():
    raise SystemExit("❌ Le chemin du fichier Cookies est incorrect ou inaccessible.")

# Copier dans un fichier temporaire à côté du script
dst = Path(__file__).parent / "Cookies_copy.db"
shutil.copy2(src, dst)
print("Copie vers    :", dst)

# Ouvrir la copie en lecture seule
conn = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
cur = conn.cursor()

cur.execute("""
    SELECT host_key, name, path
    FROM cookies
    WHERE host_key LIKE '%claude.ai%' OR host_key LIKE '%anthropic.com%'
    ORDER BY host_key, name
""")

rows = cur.fetchall()
conn.close()

print("\nCookies trouvés pour claude/anthropic :")
for host_key, name, path in rows:
    print(f"- {host_key} | {name} | {path}")

if not rows:
    print("(aucun cookie trouvé pour ces domaines)")
