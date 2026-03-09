import pandas as pd
import ast
from pathlib import Path

print("="*70)
print("📊 API MODEL PERFORMANCE ANALYSIS")
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
print(f"📋 Found {len(model_cols)} API prediction columns")

# Analyze each model prediction column
results = []

print("\n" + "="*70)
print("🔍 Analyzing each model run...")
print("="*70)

for col in model_cols:
    # Parse column name: results_run1_single_modelname
    parts = col.replace('results_', '').split('_')
    run = parts[0]  # run1 or run2
    mode = parts[1]  # single or multi
    model = '_'.join(parts[2:])  # model name
    
    # Calculate accuracy
    correct = 0
    total = 0
    
    for idx, row in df.iterrows():
        manual = row['manual_cats_list']
        predicted = str(row[col]).strip()
        
        if not manual:
            continue
        
        total += 1
        
        # Check if prediction matches (exact or subset)
        if predicted in manual:
            correct += 1
    
    accuracy = (correct / total * 100) if total > 0 else 0
    
    results.append({
        'Run': run,
        'Mode': mode,
        'Model': model,
        'Column_Name': col,
        'Correct': correct,
        'Total': total,
        'Accuracy_%': round(accuracy, 2)
    })
    
    print(f"✓ {col}: {correct}/{total} = {accuracy:.2f}%")

# Create results dataframe
results_df = pd.DataFrame(results)

# Save detailed results
Path("data/exports").mkdir(parents=True, exist_ok=True)
results_df.to_csv("data/exports/api_model_performance_detailed.csv", index=False)
print(f"\n💾 Saved: data/exports/api_model_performance_detailed.csv")

# Aggregate by model (average across all runs and modes)
print("\n" + "="*70)
print("📊 OVERALL MODEL RANKING (Averaged across runs & modes)")
print("="*70)

model_summary = results_df.groupby('Model').agg({
    'Correct': 'mean',
    'Total': 'mean',
    'Accuracy_%': 'mean'
}).round(2).sort_values('Accuracy_%', ascending=False)

print(model_summary)

model_summary.to_csv("data/exports/api_model_performance_summary.csv")
print(f"\n💾 Saved: data/exports/api_model_performance_summary.csv")

# Compare single vs multi mode
print("\n" + "="*70)
print("📊 SINGLE-LABEL vs MULTI-LABEL PROMPTING")
print("="*70)

mode_comparison = results_df.groupby('Mode').agg({
    'Accuracy_%': 'mean'
}).round(2)

print(mode_comparison)

# Compare run1 vs run2 consistency
print("\n" + "="*70)
print("📊 RUN1 vs RUN2 CONSISTENCY")
print("="*70)

run_comparison = results_df.groupby('Run').agg({
    'Accuracy_%': 'mean'
}).round(2)

print(run_comparison)

print("\n" + "="*70)
print("🎉 ANALYSIS COMPLETE!")
print("="*70)
print("\nGenerated files:")
print("  1. data/exports/api_model_performance_detailed.csv")
print("  2. data/exports/api_model_performance_summary.csv")
print("\nNext: Run per-category accuracy analysis")
