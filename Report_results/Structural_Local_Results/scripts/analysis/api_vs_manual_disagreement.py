import pandas as pd
import ast
from pathlib import Path
from collections import Counter

print("="*70)
print("📊 API PREDICTIONS vs MANUAL LABELS DISAGREEMENT")
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

print("\n" + "="*70)
print("🔍 Finding questions where ALL models disagree with manual...")
print("="*70)

# Analyze each question
disagreement_stats = []

for idx, row in df.iterrows():
    manual = row['manual_cats_list']
    
    if not manual:
        continue
    
    question_num = row['Sr. no.']
    
    # Get all predictions for this question
    predictions = []
    correct_count = 0
    
    for col in model_cols:
        pred = str(row[col]).strip()
        predictions.append(pred)
        
        if pred in manual:
            correct_count += 1
    
    total_predictions = len(predictions)
    accuracy_rate = (correct_count / total_predictions * 100) if total_predictions > 0 else 0
    
    # Most common wrong prediction
    wrong_preds = [p for p in predictions if p not in manual]
    most_common_wrong = Counter(wrong_preds).most_common(1)[0] if wrong_preds else (None, 0)
    
    disagreement_stats.append({
        'Question_Number': question_num,
        'Manual_Label': ','.join(manual),
        'Correct_Predictions': correct_count,
        'Total_Predictions': total_predictions,
        'Models_Correct_%': round(accuracy_rate, 2),
        'Most_Common_Wrong_Prediction': most_common_wrong[0] if most_common_wrong[0] else 'N/A',
        'Wrong_Count': most_common_wrong[1] if most_common_wrong[0] else 0
    })

# Create DataFrame
disagreement_df = pd.DataFrame(disagreement_stats)

# Save
Path("data/exports").mkdir(parents=True, exist_ok=True)
disagreement_df.to_csv("data/exports/api_vs_manual_disagreement.csv", index=False)

print("\n" + "="*70)
print("📊 Questions with 0% Model Agreement (Hardest)")
print("="*70)

hardest = disagreement_df[disagreement_df['Models_Correct_%'] == 0].sort_values('Question_Number')
print(f"\nFound {len(hardest)} questions where NO model got it right:")
print(hardest[['Question_Number', 'Manual_Label', 'Most_Common_Wrong_Prediction']].to_string(index=False))

print("\n" + "="*70)
print("📊 Questions with 100% Model Agreement (Easiest)")
print("="*70)

easiest = disagreement_df[disagreement_df['Models_Correct_%'] == 100].sort_values('Question_Number')
print(f"\nFound {len(easiest)} questions where ALL models got it right:")
if len(easiest) > 10:
    print(easiest[['Question_Number', 'Manual_Label']].head(10).to_string(index=False))
    print(f"... and {len(easiest)-10} more")
else:
    print(easiest[['Question_Number', 'Manual_Label']].to_string(index=False))

print("\n" + "="*70)
print("📊 Distribution of Model Agreement")
print("="*70)

agreement_dist = disagreement_df.groupby('Models_Correct_%').size().reset_index(name='Count')
print(agreement_dist.to_string(index=False))

print("\n" + "="*70)
print("🎉 ANALYSIS COMPLETE!")
print("="*70)
print("\nGenerated: data/exports/api_vs_manual_disagreement.csv")
