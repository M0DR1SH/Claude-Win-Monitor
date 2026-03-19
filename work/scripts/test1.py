import sqlite3

db_path = r"C:\Users\souli\AppData\Local\Packages\TheBrowserCompany.Arc_ttt1ap7aakyb4\LocalCache\Local\Arc\User Data\Profile 2\Network\Cookies"

conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
cur = conn.cursor()

# 1) Lister tous les cookies liés à claude / anthropic
cur.execute("""
    SELECT host_key, name, path
    FROM cookies
    WHERE host_key LIKE '%claude.ai%' OR host_key LIKE '%anthropic.com%'
    ORDER BY host_key, name
""")

rows = cur.fetchall()
conn.close()

print("Cookies trouvés pour claude/anthropic :")
for host_key, name, path in rows:
    print(f"- {host_key} | {name} | {path}")
