import pandas as pd
import ast
from pathlib import Path
import itertools

print("="*70)
print("📊 PAIRWISE MODEL AGREEMENT ANALYSIS (Run1 Only)")
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

# Short names for display
model_short_names = {
    'anthropic_claude-sonnet-4.5': 'Claude',
    'deepseek_deepseek-v3.2': 'DeepSeek',
    'google_gemini-2.5-flash': 'Gemini',
    'openai_gpt-5.2': 'GPT-5.2',
    'openai_gpt-oss-120b': 'GPT-OSS',
    'qwen_qwen3-coder': 'Qwen'
}

results = []

for mode in ['single', 'multi']:
    print(f"\n" + "="*70)
    print(f"🔍 Mode: {mode.upper()}-LABEL")
    print("="*70)
    
    # Get all pairwise combinations
    for model1, model2 in itertools.combinations(models, 2):
        col1 = f"results_run1_{mode}_{model1}"
        col2 = f"results_run1_{mode}_{model2}"
        
        if col1 not in df.columns or col2 not in df.columns:
            continue
        
        # Calculate agreement metrics
        total = 0
        exact_agreement = 0
        both_correct = 0
        both_wrong = 0
        disagree_both_wrong = 0
        disagree_one_correct = 0
        
        for idx, row in df.iterrows():
            manual = row['manual_cats_list']
            
            if not manual:
                continue
            
            total += 1
            
            pred1 = str(row[col1]).strip()
            pred2 = str(row[col2]).strip()
            
            correct1 = pred1 in manual
            correct2 = pred2 in manual
            
            # Exact agreement
            if pred1 == pred2:
                exact_agreement += 1
                
                if correct1 and correct2:
                    both_correct += 1
                elif not correct1 and not correct2:
                    both_wrong += 1
            else:
                # Disagreement
                if correct1 or correct2:
                    disagree_one_correct += 1
                else:
                    disagree_both_wrong += 1
        
        agreement_rate = (exact_agreement / total * 100) if total > 0 else 0
        
        results.append({
            'Mode': mode,
            'Model_1': model_short_names[model1],
            'Model_2': model_short_names[model2],
            'Total_Questions': total,
            'Exact_Agreement': exact_agreement,
            'Agreement_Rate_%': round(agreement_rate, 2),
            'Both_Correct': both_correct,
            'Both_Wrong': both_wrong,
            'Disagree_One_Correct': disagree_one_correct,
            'Disagree_Both_Wrong': disagree_both_wrong
        })
        
        print(f"\n{model_short_names[model1]} vs {model_short_names[model2]}:")
        print(f"   Agreement rate: {agreement_rate:.2f}%")
        print(f"   Both correct: {both_correct}, Both wrong: {both_wrong}")
        print(f"   Disagree (one correct): {disagree_one_correct}")

# Save results
results_df = pd.DataFrame(results)
Path("data/exports").mkdir(parents=True, exist_ok=True)
results_df.to_csv("data/exports/api_pairwise_agreement.csv", index=False)

# Create agreement matrix for each mode
for mode in ['single', 'multi']:
    mode_data = results_df[results_df['Mode'] == mode]
    
    # Create matrix
    matrix = pd.DataFrame(index=model_short_names.values(), columns=model_short_names.values())
    matrix = matrix.fillna(0)
    
    for _, row in mode_data.iterrows():
        m1 = row['Model_1']
        m2 = row['Model_2']
        agr = row['Agreement_Rate_%']
        
        matrix.loc[m1, m2] = agr
        matrix.loc[m2, m1] = agr
    
    # Diagonal is 100% (self-agreement)
    for model in model_short_names.values():
        matrix.loc[model, model] = 100.0
    
    print(f"\n" + "="*70)
    print(f"📊 AGREEMENT MATRIX: {mode.upper()}-LABEL")
    print("="*70)
    print("\n" + str(matrix))
    
    matrix.to_csv(f"data/exports/api_pairwise_agreement_matrix_{mode}.csv")

print("\n" + "="*70)
print("🎉 ANALYSIS COMPLETE!")
print("="*70)
print("\nGenerated files:")
print("  - data/exports/api_pairwise_agreement.csv")
print("  - data/exports/api_pairwise_agreement_matrix_single.csv")
print("  - data/exports/api_pairwise_agreement_matrix_multi.csv")
