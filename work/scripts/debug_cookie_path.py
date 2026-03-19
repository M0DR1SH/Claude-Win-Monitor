import os, urllib.parse, sqlite3
from pathlib import Path

APP_DATA = Path(os.environ.get('LOCALAPPDATA', ''))
cookies_path = APP_DATA / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Network' / 'Cookies'
print('Existe:', cookies_path.exists())
print('Chemin:', cookies_path)

# URI Windows correcte
p = cookies_path.as_posix()
uri = 'file:///' + urllib.parse.quote(p, safe='/:') + '?mode=ro&immutable=1'
print('URI:', uri)

# Test connexion
try:
    conn = sqlite3.connect(uri, uri=True)
    print('Connexion OK')
    conn.close()
except Exception as e:
    print('Erreur URI:', e)

# Fallback : copie via robocopy (bypass lock)
import subprocess, tempfile, shutil
tmp_dir = tempfile.mkdtemp()
result = subprocess.run(
    ['robocopy', str(cookies_path.parent), tmp_dir, 'Cookies', '/B', '/NJH', '/NJS', '/NFL', '/NDL'],
    capture_output=True
)
tmp_cookies = Path(tmp_dir) / 'Cookies'
print('Robocopy retour:', result.returncode, '| Fichier copie:', tmp_cookies.exists())
if tmp_cookies.exists():
    try:
        conn = sqlite3.connect(str(tmp_cookies))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print('Tables:', cursor.fetchall())
        conn.close()
    except Exception as e:
        print('Erreur SQLite copie:', e)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
