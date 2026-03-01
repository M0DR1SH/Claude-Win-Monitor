#!/usr/bin/env python3
# claude_logs_stats_v3.py - CORRIGÉ + robuste
from pathlib import Path
import json
import glob
from datetime import datetime
from collections import defaultdict
import re

def safe_parse_ts(ts):
    """Parse timestamp safe (str/int/None)"""
    if not ts:
        return None
    try:
        if isinstance(ts, str):
            ts = int(ts)
        return datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
    except:
        return None

def parse_line(line):
    """Parse TOUS formats"""
    try:
        data = json.loads(line.strip())
        
        # Tokens (multi-formats)
        input_t = (data.get('usage', {}).get('input_tokens', 0) or
                   data.get('input_tokens', 0) or
                   data.get('model_tokens', {}).get('input', 0) or 0)
        output_t = (data.get('usage', {}).get('output_tokens', 0) or
                    data.get('output_tokens', 0) or
                    data.get('model_tokens', {}).get('output', 0) or 0)
        cache_t = data.get('usage', {}).get('cache_read_input_tokens', 0)
        
        return {
            'input': input_t, 'output': output_t, 'cache': cache_t,
            'model': data.get('model', 'unknown'),
            'role': data.get('role', ''),
            'ts': safe_parse_ts(data.get('timestamp'))
        }
    except:
        return None

def analyze_all_logs():
    home = Path.home() / ".claude"
    jsonl_files = list(glob.glob(str(home / "**/*.jsonl"), recursive=True))
    
    print(f"📊 Analyse {len(jsonl_files)} fichiers...")
    
    stats = defaultdict(lambda: {'input': 0, 'output': 0, 'cache': 0, 'msgs': 0})
    models = defaultdict(int)
    daily = defaultdict(int)
    
    for filepath in jsonl_files:
        content = Path(filepath).read_text(errors='ignore')
        lines_processed = 0
        
        for line in content.splitlines():
            parsed = parse_line(line)
            if parsed:
                stats[str(filepath)]['input'] += parsed['input']
                stats[str(filepath)]['output'] += parsed['output']
                stats[str(filepath)]['msgs'] += 1
                models[parsed['model']] += 1
                
                if parsed['ts']:
                    daily[parsed['ts']] += 1
                lines_processed += 1
        
        if lines_processed:
            print(f"  ✓ {Path(filepath).name}: {lines_processed} lignes")
    
    # RÉSULTATS
    total_input = sum(f['input'] for f in stats.values())
    total_output = sum(f['output'] for f in stats.values())
    total_msgs = sum(f['msgs'] for f in stats.values())
    
    print("\n" + "="*70)
    print("📊 STATS LOGS CLAUDE CODE")
    print("="*70)
    print(f"📁 Fichiers: {len(stats)}")
    print(f"💬 Messages: {total_msgs:,}")
    print(f"🔤 Input: {total_input:,}")
    print(f"🔤 Output: {total_output:,}")
    print(f"📊 Total: {total_input + total_output:,}")
    
    if models:
        print(f"\n🤖 Modèles (top 5)")
        for model, count in sorted(models.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {model}: {count}")
    
    if daily:
        print(f"\n📅 Jours actifs (top 7)")
        for date, msgs in sorted(daily.items(), key=lambda x: x[1], reverse=True)[:7]:
            print(f"  {date}: {msgs}")
    
    # Top fichiers
    top_files = sorted(stats.items(), key=lambda x: x[1]['input'] + x[1]['output'], reverse=True)[:5]
    if top_files:
        print(f"\n📁 Top 5 fichiers (tokens)")
        for file, s in top_files:
            print(f"  {Path(file).name}: {s['input']:,}i/{s['output']:,}o")

if __name__ == "__main__":
    analyze_all_logs()
