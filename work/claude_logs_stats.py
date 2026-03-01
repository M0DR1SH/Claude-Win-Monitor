#!/usr/bin/env python3
# claude_logs_finder_stats.py - TROUVE + analyse TOUS logs Claude Code
from pathlib import Path
import json
import glob
from datetime import datetime
from collections import defaultdict

def find_and_analyze_logs():
    home = Path.home() / ".claude"
    if not home.exists():
        print("❌ Dossier .claude absent")
        return
    
    # ══ RECHERCHE AGRESSIVE ══
    print("🔍 Recherche exhaustive logs Claude Code...")
    
    # Patterns possibles (Windows/macOS/Linux)
    patterns = [
        "**/*.jsonl",
        "**/*.chat.jsonl", 
        "**/session*.jsonl",
        "**/chat*.jsonl",
        "projects/**/*",
        "**/history.jsonl"
    ]
    
    all_files = []
    for pattern in patterns:
        files = list(home.glob(pattern))
        all_files.extend(files)
    
    jsonl_files = [f for f in all_files if f.suffix == '.jsonl']
    
    print(f"📁 {len(jsonl_files)} fichiers JSONL trouvés")
    for f in jsonl_files[:10]:  # Top 10
        print(f"  📄 {f}")
    
    if not jsonl_files:
        print("\n❌ SOLUTION: Lancez 1 session Claude Code dans un projet")
        print("   → Crée automatiquement les .jsonl")
        return
    
    # ══ ANALYSE ══
    stats = {
        'input_tokens': 0, 'output_tokens': 0, 'cache_tokens': 0,
        'messages': 0, 'sessions': len(jsonl_files),
        'daily': defaultdict(int), 'models': defaultdict(int)
    }
    
    for filepath in jsonl_files:
        content = filepath.read_text(errors='ignore')
        for line in content.splitlines():
            if not line.strip(): continue
            try:
                data = json.loads(line)
                usage = data.get('usage', {})
                stats['input_tokens'] += usage.get('input_tokens', 0)
                stats['output_tokens'] += usage.get('output_tokens', 0)
                stats['cache_tokens'] += usage.get('cache_read_input_tokens', 0)
                stats['messages'] += 1
                
                # Date
                ts = data.get('timestamp')
                if ts:
                    date = datetime.fromtimestamp(ts/1000).date()
                    stats['daily'][date] += 1
                
                # Modèle
                model = data.get('model', 'unknown')
                stats['models'][model] += 1
                
            except:
                pass  # Ignore lignes invalides
    
    # ══ AFFICHAGE ══
    print("\n" + "="*60)
    print("📊 STATS LOGS CLAUDE CODE")
    print("="*60)
    print(f"📁 Sessions analysées : {stats['sessions']}")
    print(f"💬 Messages totaux   : {stats['messages']:,}")
    print(f"🔤 Tokens input      : {stats['input_tokens']:,}")
    print(f"🔤 Tokens output     : {stats['output_tokens']:,}")
    print(f"💾 Cache tokens      : {stats['cache_tokens']:,}")
    print(f"📊 Total tokens      : {sum([stats['input_tokens'], stats['output_tokens']]):,}")
    
    print(f"\n🤖 Modèles (top 3)")
    for model in sorted(stats['models'].items(), key=lambda x: x[1], reverse=True)[:3]:
        print(f"  {model[0]}: {model[1]}")
    
    print(f"\n📅 Usage récent (top 5)")
    for date in sorted(stats['daily'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {date[0]}: {date[1]} messages")
    
    print(f"\n🔗 Fichiers (top 5 récents)")
    recent = sorted(jsonl_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    for f in recent:
        print(f"  {f.relative_to(home)}")

if __name__ == "__main__":
    find_and_analyze_logs()
