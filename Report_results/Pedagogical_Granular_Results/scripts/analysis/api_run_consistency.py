import pandas as pd
import ast
from pathlib import Path

print("="*70)
print("📊 RUN1 vs RUN2 CONSISTENCY ANALYSIS")
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
print("🔍 Comparing Run1 vs Run2 for each model...")
print("="*70)

results = []

for model in models:
    print(f"\n📊 {model}")
    
    for mode in ['single', 'multi']:
        run1_col = f"results_run1_{mode}_{model}"
        run2_col = f"results_run2_{mode}_{model}"
        
        if run1_col not in df.columns or run2_col not in df.columns:
            continue
        
        # Calculate metrics
        run1_correct = 0
        run2_correct = 0
        agreement = 0
        both_correct = 0
        both_wrong = 0
        total = 0
        
        for idx, row in df.iterrows():
            manual = row['manual_cats_list']
            
            if not manual:
                continue
            
            total += 1
            
            run1_pred = str(row[run1_col]).strip()
            run2_pred = str(row[run2_col]).strip()
            
            run1_match = run1_pred in manual
            run2_match = run2_pred in manual
            
            if run1_match:
                run1_correct += 1
            if run2_match:
                run2_correct += 1
            
            # Agreement: both gave same prediction (regardless of correctness)
            if run1_pred == run2_pred:
                agreement += 1
            
            # Both correct
            if run1_match and run2_match:
                both_correct += 1
            
            # Both wrong
            if not run1_match and not run2_match:
                both_wrong += 1
        
        run1_acc = (run1_correct / total * 100) if total > 0 else 0
        run2_acc = (run2_correct / total * 100) if total > 0 else 0
        agreement_rate = (agreement / total * 100) if total > 0 else 0
        consistency = (both_correct + both_wrong) / total * 100 if total > 0 else 0
        
        results.append({
            'Model': model,
            'Mode': mode,
            'Run1_Correct': run1_correct,
            'Run2_Correct': run2_correct,
            'Total': total,
            'Run1_Accuracy_%': round(run1_acc, 2),
            'Run2_Accuracy_%': round(run2_acc, 2),
            'Agreement_Rate_%': round(agreement_rate, 2),
            'Consistency_%': round(consistency, 2),
            'Accuracy_Difference_%': round(abs(run1_acc - run2_acc), 2)
        })
        
        print(f"   {mode.capitalize()}:")
        print(f"      Run1 accuracy: {run1_acc:.2f}%")
        print(f"      Run2 accuracy: {run2_acc:.2f}%")
        print(f"      Agreement rate: {agreement_rate:.2f}%")
        print(f"      Consistency: {consistency:.2f}%")

# Create DataFrame
results_df = pd.DataFrame(results)

# Save
Path("data/exports").mkdir(parents=True, exist_ok=True)
results_df.to_csv("data/exports/api_run_consistency.csv", index=False)

print("\n" + "="*70)
print("📊 SUMMARY: Most Consistent Models")
print("="*70)

summary = results_df.groupby('Model').agg({
    'Agreement_Rate_%': 'mean',
    'Consistency_%': 'mean',
    'Accuracy_Difference_%': 'mean'
}).round(2).sort_values('Agreement_Rate_%', ascending=False)

print(summary)

print("\n" + "="*70)
print("🎉 ANALYSIS COMPLETE!")
print("="*70)
print("\nGenerated: data/exports/api_run_consistency.csv")
