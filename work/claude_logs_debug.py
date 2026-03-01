#!/usr/bin/env python3
# claude_logs_debug.py - DEBUG + parse réel
from pathlib import Path
import json
import glob

home = Path.home() / ".claude"
files = glob.glob(str(home / "**/*.jsonl"), recursive=True)

print("🔍 DEBUG FORMAT JSONL (top 3 fichiers)")
for filepath in files[:3]:
    print(f"\n📄 {Path(filepath).name}")
    content = Path(filepath).read_text(errors='ignore')
    lines = content.splitlines()[:5]  # 5 premières lignes
    
    for i, line in enumerate(lines, 1):
        if line.strip():
            try:
                data = json.loads(line)
                print(f"  L{i}: keys={list(data.keys())} | usage={data.get('usage')}")
                # Cherche TOUS champs numériques possibles
                for k, v in data.items():
                    if isinstance(v, (int, float)) and v > 10:
                        print(f"    → {k}: {v}")
            except:
                print(f"  L{i}: non-JSON")

# Stats rapides
tokens = 0
for f in files[:10]:  # Top 10
    for line in Path(f).read_text().splitlines()[:100]:
        try:
            data = json.loads(line)
            # Cherche n'importe quel nombre > 10
            for v in data.values():
                if isinstance(v, int) and v > 10:
                    tokens += v
                    break
        except:
            pass

print(f"\n💡 Tokens détectés (brut): {tokens:,}")
print("📝 Copie 1 ligne complète → je parse exactement")
