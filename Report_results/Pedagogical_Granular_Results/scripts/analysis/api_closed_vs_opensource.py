import pandas as pd
import ast
from pathlib import Path

print("="*70)
print("📊 CLOSED vs OPEN SOURCE MODEL COMPARISON (Run1 Only)")
print("="*70)

# Load consolidated data
df = pd.read_csv("data/processed/yaksh_100_qns_consolidated.csv")
print(f"\n✅ Loaded: {df.shape}")

# Parse manual categories
def parse_categories(cat_str):
    if pd.isna(cat_str) or cat_str == '':
        return []
    if isinstance(cat_str, str):
        if cat_str.startswith('['):
            return ast.literal_eval(cat_str)
        else:
            return [c.strip() for c in cat_str.split(',') if c.strip()]
    return []

df['manual_cats_list'] = df['manual_categories'].apply(parse_categories)

# Categorize models
closed_source = {
    'anthropic_claude-sonnet-4.5': 'Anthropic Claude Sonnet 4.5',
    'google_gemini-2.5-flash': 'Google Gemini 2.5 Flash',
    'openai_gpt-5.2': 'OpenAI GPT-5.2'
}

open_source = {
    'deepseek_deepseek-v3.2': 'DeepSeek v3.2',
    'openai_gpt-oss-120b': 'OpenAI GPT-OSS-120B',
    'qwen_qwen3-coder': 'Qwen3 Coder'
}

results = []

for mode in ['single', 'multi']:
    print(f"\n" + "="*70)
    print(f"🔍 Mode: {mode.upper()}-LABEL")
    print("="*70)
    
    # Analyze closed source models
    print("\n📊 CLOSED SOURCE MODELS:")
    closed_results = []
    
    for model_key, model_name in closed_source.items():
        col = f"results_run1_{mode}_{model_key}"
        
        if col not in df.columns:
            continue
        
        correct = 0
        total = 0
        
        for idx, row in df.iterrows():
            manual = row['manual_cats_list']
            
            if not manual:
                continue
            
            total += 1
            pred = str(row[col]).strip()
            
            if pred in manual:
                correct += 1
        
        accuracy = (correct / total * 100) if total > 0 else 0
        
        closed_results.append({
            'Model': model_name,
            'Correct': correct,
            'Total': total,
            'Accuracy_%': round(accuracy, 2)
        })
        
        print(f"   {model_name}: {accuracy:.2f}%")
    
    # Analyze open source models
    print("\n📊 OPEN SOURCE MODELS:")
    open_results = []
    
    for model_key, model_name in open_source.items():
        col = f"results_run1_{mode}_{model_key}"
        
        if col not in df.columns:
            continue
        
        correct = 0
        total = 0
        
        for idx, row in df.iterrows():
            manual = row['manual_cats_list']
            
            if not manual:
                continue
            
            total += 1
            pred = str(row[col]).strip()
            
            if pred in manual:
                correct += 1
        
        accuracy = (correct / total * 100) if total > 0 else 0
        
        open_results.append({
            'Model': model_name,
            'Correct': correct,
            'Total': total,
            'Accuracy_%': round(accuracy, 2)
        })
        
        print(f"   {model_name}: {accuracy:.2f}%")
    
    # Calculate averages
    closed_avg = sum(r['Accuracy_%'] for r in closed_results) / len(closed_results) if closed_results else 0
    open_avg = sum(r['Accuracy_%'] for r in open_results) / len(open_results) if open_results else 0
    
    print(f"\n📊 SUMMARY:")
    print(f"   Closed Source Average: {closed_avg:.2f}%")
    print(f"   Open Source Average: {open_avg:.2f}%")
    print(f"   Difference: {closed_avg - open_avg:+.2f}%")
    
    results.append({
        'Mode': mode,
        'Closed_Source_Avg_%': round(closed_avg, 2),
        'Open_Source_Avg_%': round(open_avg, 2),
        'Difference_%': round(closed_avg - open_avg, 2),
        'Best_Closed': max(closed_results, key=lambda x: x['Accuracy_%'])['Model'] if closed_results else 'N/A',
        'Best_Open': max(open_results, key=lambda x: x['Accuracy_%'])['Model'] if open_results else 'N/A'
    })

# Save results
results_df = pd.DataFrame(results)
Path("data/exports").mkdir(parents=True, exist_ok=True)
results_df.to_csv("data/exports/api_closed_vs_opensource_summary.csv", index=False)

print("\n" + "="*70)
print("📊 OVERALL COMPARISON")
print("="*70)
print(results_df.to_string(index=False))

print("\n" + "="*70)
print("🎉 ANALYSIS COMPLETE!")
print("="*70)
print("\nGenerated: data/exports/api_closed_vs_opensource_summary.csv")
