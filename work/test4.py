import sqlite3
from pathlib import Path

db_path = Path(r"C:\Users\souli\AppData\Local\Packages\TheBrowserCompany.Arc_ttt1ap7aakyb4\LocalCache\Local\Arc\User Data\Profile 2\Network\Cookies")

print("Chemin source :", db_path)
print("Existe ?      :", db_path.exists())
print("Est un fichier:", db_path.is_file())

if not db_path.is_file():
    raise SystemExit("❌ Fichier introuvable.")

conn = sqlite3.connect(str(db_path))  # pas de mode=ro, pas d'URI
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
