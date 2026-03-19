#!/usr/bin/env python3
# claude_logs_stats_v2.py - Analyse formats JSONL VARIÉS Claude Code
from pathlib import Path
import json
import glob
from datetime import datetime
from collections import defaultdict

def parse_line(line):
    """Parse TOUS formats possibles"""
    try:
        data = json.loads(line)
        
        # Format 1: usage.input_tokens (standard)
        usage = data.get('usage', {})
        input_t = usage.get('input_tokens', 0)
        output_t = usage.get('output_tokens', 0)
        cache_t = usage.get('cache_read_input_tokens', 0)
        
        # Format 2: tokens plats (agent/subagent)
        if input_t == 0:
            input_t = data.get('input_tokens', 0)
            output_t = data.get('output_tokens', 0)
        
        # Format 3: model_tokens (récents)
        if input_t == 0:
            input_t = data.get('model_tokens', {}).get('input', 0)
            output_t = data.get('model_tokens', {}).get('output', 0)
        
        return {
            'input': input_t, 'output': output_t, 'cache': cache_t,
            'model': data.get('model', 'unknown'),
            'role': data.get('role', ''),
            'ts': data.get('timestamp')
        }
    except:
        return None

def analyze_all_logs():
    home = Path.home() / ".claude"
    jsonl_files = glob.glob(str(home / "**/*.jsonl"), recursive=True)
    
    if not jsonl_files:
        print("❌ Aucun .jsonl")
        return
    
    stats = defaultdict(lambda: {'input': 0, 'output': 0, 'cache': 0, 'msgs': 0})
    models = defaultdict(int)
    daily = defaultdict(int)
    
    print(f"📊 Analyse {len(jsonl_files)} fichiers...")
    
    for filepath in jsonl_files:
        content = Path(filepath).read_text(errors='ignore')
        for line in content.splitlines():
            parsed = parse_line(line)
            if parsed:
                stats[filepath]['input'] += parsed['input']
                stats[filepath]['output'] += parsed['output']
                stats[filepath]['msgs'] += 1
                
                models[parsed['model']] += 1
                
                if parsed['ts']:
                    date = datetime.fromtimestamp(parsed['ts']/1000).strftime('%Y-%m-%d')
                    daily[date] += 1
    
    # ══ RÉSULTATS ══
    total_input = sum(f['input'] for f in stats.values())
    total_output = sum(f['output'] for f in stats.values())
    
    print("\n" + "="*70)
    print("📊 STATS LOGS CLAUDE CODE (214 sessions)")
    print("="*70)
    print(f"💬 Messages: {sum(f['msgs'] for f in stats.values()):,}")
    print(f"🔤 Input total: {total_input:,}")
    print(f"🔤 Output total: {total_output:,}")
    print(f"📊 GRAND TOTAL: {total_input + total_output:,}")
    
    print("\n🤖 Top modèles")
    for model, count in sorted(models.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {model}: {count}")
    
    print("\n📅 Top jours")
    for date, msgs in sorted(daily.items(), key=lambda x: x[1], reverse=True)[:7]:
        print(f"  {date}: {msgs} messages")
    
    print("\n📁 Top 5 fichiers (tokens)")
    top_files = sorted(stats.items(), key=lambda x: x[1]['input'] + x[1]['output'], reverse=True)[:5]
    for file, s in top_files:
        print(f"  {Path(file).name}: {s['input']:,}i + {s['output']:,}o")

if __name__ == "__main__":
    analyze_all_logs()
