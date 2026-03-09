import pandas as pd
import os
import ast
from pathlib import Path

print("="*70)
print("📊 CONSOLIDATING: QUESTIONS + MANUAL LABELS + MODEL PREDICTIONS")
print("="*70)

# Create folders
Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/exports").mkdir(parents=True, exist_ok=True)

# STEP 1: Load original questions
questions_csv = "data/raw/yaksh_100_qns.csv"
df_questions = pd.read_csv(questions_csv)
print(f"\n✅ Loaded questions: {questions_csv}")
print(f"   Shape: {df_questions.shape}")

# STEP 2: Load manual labels from Colab
manual_labels_csv = "data/manual_labels/manual_labels_cleaned.csv"
df_manual = pd.read_csv(manual_labels_csv)
print(f"\n✅ Loaded manual labels: {manual_labels_csv}")
print(f"   Shape: {df_manual.shape}")

# Convert string representation of lists to actual lists if needed
if df_manual['final_categories'].dtype == 'object':
    df_manual['final_categories'] = df_manual['final_categories'].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else x
    )

# Convert list to comma-separated string for CSV storage
df_manual['manual_categories'] = df_manual['final_categories'].apply(
    lambda x: ','.join(x) if isinstance(x, list) else str(x)
)

# Merge questions with manual labels
df = pd.merge(
    df_questions,
    df_manual[['Sr. no.', 'manual_categories']],
    on='Sr. no.',
    how='left'
)

print(f"\n✅ Merged questions + manual labels")
print(f"   Shape: {df.shape}")

# STEP 3: Add model predictions
runs = ["results_run1", "results_run2"]
modes = ["single", "multi"]

columns_added = 0

for run in runs:
    for mode in modes:
        folder_path = f"{run}/{mode}"
        
        if not os.path.exists(folder_path):
            print(f"\n⚠️  Skipping {folder_path}")
            continue
        
        print(f"\n📂 Processing: {folder_path}/")
        
        txt_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.txt')])
        
        for txt_file in txt_files:
            file_path = f"{folder_path}/{txt_file}"
            model_name = txt_file.replace(f'_{mode}.txt', '')
            
            # Read predictions
            predictions = {}
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                q_id = int(parts[0])
                                category = parts[1]
                                predictions[q_id] = category
                            except ValueError:
                                continue
            
            # Create prediction column
            pred_list = [predictions.get(i, '') for i in range(1, 101)]
            col_name = f"{run}_{mode}_{model_name}"
            df[col_name] = pred_list
            columns_added += 1
            print(f"   ✅ {model_name}: {len(predictions)} predictions")

# STEP 4: Save consolidated data
output_csv = "data/processed/yaksh_100_qns_consolidated.csv"
df.to_csv(output_csv, index=False)

print(f"\n{'='*70}")
print(f"💾 SAVED: {output_csv}")
print(f"{'='*70}")

# STEP 5: Generate summary
print(f"\n📊 FINAL DATASET SUMMARY:")
print(f"   Total questions: {len(df)}")
print(f"   Total columns: {len(df.columns)}")

original_cols = [c for c in df.columns if not c.startswith('results_')]
model_cols = [c for c in df.columns if c.startswith('results_')]

print(f"\n   📋 Data columns ({len(original_cols)}):")
for col in original_cols:
    print(f"      - {col}")

print(f"\n   🤖 Model prediction columns ({len(model_cols)}):")
for col in model_cols[:6]:
    print(f"      - {col}")
if len(model_cols) > 6:
    print(f"      ... and {len(model_cols) - 6} more")

# Save summary
summary_file = "data/exports/consolidation_summary.txt"
with open(summary_file, 'w') as f:
    f.write("="*70 + "\n")
    f.write("COMPLETE DATA CONSOLIDATION SUMMARY\n")
    f.write("="*70 + "\n\n")
    f.write(f"Sources:\n")
    f.write(f"  1. Questions: {questions_csv}\n")
    f.write(f"  2. Manual labels: {manual_labels_csv}\n")
    f.write(f"  3. Model predictions: {runs} × {modes}\n\n")
    f.write(f"Output: {output_csv}\n\n")
    f.write(f"Dataset structure:\n")
    f.write(f"  Total questions: {len(df)}\n")
    f.write(f"  Original columns: {len(original_cols)}\n")
    f.write(f"  Model prediction columns: {len(model_cols)}\n")
    f.write(f"  Total columns: {len(df.columns)}\n\n")
    f.write("All columns:\n")
    for col in df.columns:
        f.write(f"  - {col}\n")

print(f"\n💾 Summary saved: {summary_file}")
print(f"\n🎉 CONSOLIDATION COMPLETE!")
