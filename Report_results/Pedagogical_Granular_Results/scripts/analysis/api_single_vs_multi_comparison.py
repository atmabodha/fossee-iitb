import pandas as pd
import ast
from pathlib import Path

print("="*70)
print("📊 SINGLE vs MULTI-LABEL PROMPTING COMPARISON")
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

# Get model columns
model_cols = [c for c in df.columns if c.startswith('results_')]

# Define models
models = [
    'anthropic_claude-sonnet-4.5',
    'deepseek_deepseek-v3.2',
    'google_gemini-2.5-flash',
    'openai_gpt-5.2',
    'openai_gpt-oss-120b',
    'qwen_qwen3-coder'
]

print("\n" + "="*70)
print("🔍 Comparing Single vs Multi-label prompting...")
print("="*70)

results = []

for model in models:
    print(f"\n📊 {model}")
    
    for run in ['run1', 'run2']:
        # Get single and multi columns for this run
        single_col = f"results_{run}_single_{model}"
        multi_col = f"results_{run}_multi_{model}"
        
        if single_col not in df.columns or multi_col not in df.columns:
            continue
        
        # Calculate accuracy for single
        single_correct = 0
        multi_correct = 0
        total = 0
        
        for idx, row in df.iterrows():
            manual = row['manual_cats_list']
            
            if not manual:
                continue
            
            total += 1
            
            single_pred = str(row[single_col]).strip()
            multi_pred = str(row[multi_col]).strip()
            
            if single_pred in manual:
                single_correct += 1
            
            if multi_pred in manual:
                multi_correct += 1
        
        single_acc = (single_correct / total * 100) if total > 0 else 0
        multi_acc = (multi_correct / total * 100) if total > 0 else 0
        improvement = multi_acc - single_acc
        
        results.append({
            'Model': model,
            'Run': run,
            'Single_Correct': single_correct,
            'Multi_Correct': multi_correct,
            'Total': total,
            'Single_Accuracy_%': round(single_acc, 2),
            'Multi_Accuracy_%': round(multi_acc, 2),
            'Improvement_%': round(improvement, 2)
        })
        
        print(f"   {run}:")
        print(f"      Single: {single_correct}/{total} = {single_acc:.2f}%")
        print(f"      Multi:  {multi_correct}/{total} = {multi_acc:.2f}%")
        print(f"      Improvement: {improvement:+.2f}%")

# Create DataFrame
results_df = pd.DataFrame(results)

# Save
Path("data/exports").mkdir(parents=True, exist_ok=True)
results_df.to_csv("data/exports/api_single_vs_multi_comparison.csv", index=False)

print("\n" + "="*70)
print("📊 SUMMARY: Average Improvement with Multi-Label")
print("="*70)

summary = results_df.groupby('Model').agg({
    'Single_Accuracy_%': 'mean',
    'Multi_Accuracy_%': 'mean',
    'Improvement_%': 'mean'
}).round(2).sort_values('Improvement_%', ascending=False)

print(summary)

print("\n" + "="*70)
print("📊 Overall Average")
print("="*70)
print(f"Single-label average: {results_df['Single_Accuracy_%'].mean():.2f}%")
print(f"Multi-label average:  {results_df['Multi_Accuracy_%'].mean():.2f}%")
print(f"Average improvement:  {results_df['Improvement_%'].mean():+.2f}%")

print("\n" + "="*70)
print("🎉 ANALYSIS COMPLETE!")
print("="*70)
print("\nGenerated: data/exports/api_single_vs_multi_comparison.csv")
