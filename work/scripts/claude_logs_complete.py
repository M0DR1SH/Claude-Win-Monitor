#!/usr/bin/env python3
# claude_logs_complete.py - MAX stats depuis tes 214 fichiers
from pathlib import Path
import json
import glob
from collections import Counter
from datetime import datetime

home = Path.home() / ".claude"
files = glob.glob(str(home / "**/*.jsonl"), recursive=True)

print(f"📊 ANALYSE COMPLÈTE {len(files)} FICHIERS")

# 1. HISTORIQUE COMMANDE (history.jsonl)
history_file = home / "history.jsonl"
if history_file.exists():
    cmds = []
    ts = []
    for line in history_file.read_text(errors='ignore').splitlines():
        try:
            data = json.loads(line)
            cmds.append(data.get('display', ''))
            ts.append(data.get('timestamp', 0))
        except:
            pass
    
    print(f"\n💬 HISTORIQUE ({len(cmds)} commandes)")
    print("Top 10 commandes:")
    for cmd, count in Counter(cmds).most_common(10):
        if cmd:
            print(f"  {count}x {cmd[:60]}")
    
    if ts:
        recent = sorted(ts)[-5:]
        print("5 dernières:")
        for t in recent:
            print(f"  {datetime.fromtimestamp(t/1000)}")

# 2. SESSIONS / PROJETS
projects = Counter()
for f in files:
    if 'projects' in str(f):
        proj = Path(f).parts[-3] if len(Path(f).parts) > 2 else "root"
        projects[proj] += 1

print(f"\n🏗️ PROJETS ({len(projects)})")
for proj, count in projects.most_common(5):
    print(f"  {proj}: {count} sessions")

# 3. TYPES FICHIERS
types = Counter(Path(f).name.split('-')[0] for f in files if '-' in Path(f).name)
print(f"\n📁 TYPES SESSIONS (top 5)")
for t, count in types.most_common(5):
    print(f"  {t}: {count}")

print("\n✅ Stats disponibles: historique, projets, activité !")
print("⚠ Tokens: non stockés (placeholders seulement)")
