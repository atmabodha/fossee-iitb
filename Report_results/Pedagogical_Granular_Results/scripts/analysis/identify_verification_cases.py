"""Identify cases needing manual verification"""
import pandas as pd

df = pd.read_csv("data/exports/multi_label_only_detailed.csv")

print("=" * 80)
print("🔍 CASES FOR MANUAL VERIFICATION")
print("=" * 80)

# Top models for reference
top_models = ['openai_gpt-5.2', 'openai_gpt-oss-120b', 'anthropic_claude-sonnet-4.5']
top_df = df[df['model'].isin(top_models)]

# Case 1: Complete mismatches (Jaccard=0, but both have labels)
mismatches = top_df[
    (top_df['case_d_jaccard'] == 0.0) & 
    (top_df['pred_size'] > 0) & 
    (top_df['manual_size'] > 0)
]

print(f"\n1️⃣ Complete Mismatches (top models predicted wrong): {len(mismatches)} cases")
print("   → May indicate manual label errors or difficult cases\n")
if len(mismatches) > 0:
    print(mismatches[['sample_id', 'model', 'pred_labels', 'manual_labels']].head(10).to_string(index=False))

# Case 2: Partial matches (0 < Jaccard < 1)
partial = top_df[
    (top_df['case_d_jaccard'] > 0.0) & 
    (top_df['case_d_jaccard'] < 1.0)
]

print(f"\n\n2️⃣ Partial Matches (ambiguous cases): {len(partial)} cases")
print("   → Model found some errors but not all\n")
if len(partial) > 0:
    print(partial[['sample_id', 'model', 'pred_labels', 'manual_labels', 'case_d_jaccard']].head(10).to_string(index=False))

# Case 3: Model consensus disagrees with manual
consensus = df.groupby('sample_id').agg({
    'pred_labels': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'manual_labels': 'first',
    'case_d_jaccard': 'mean'
}).reset_index()

low_consensus = consensus[consensus['case_d_jaccard'] < 0.3]

print(f"\n\n3️⃣ Low Consensus (models disagree with manual): {len(low_consensus)} samples")
print("   → Multiple models agree but differ from manual labels\n")
if len(low_consensus) > 0:
    print(low_consensus[['sample_id', 'pred_labels', 'manual_labels', 'case_d_jaccard']].head(10).to_string(index=False))

# Save for manual review
mismatches[['sample_id', 'model', 'pred_labels', 'manual_labels', 'run']].to_csv(
    'data/exports/verification_complete_mismatches.csv', index=False
)
partial[['sample_id', 'model', 'pred_labels', 'manual_labels', 'case_d_jaccard']].to_csv(
    'data/exports/verification_partial_matches.csv', index=False
)
low_consensus.to_csv('data/exports/verification_low_consensus.csv', index=False)

print(f"\n\n💾 Saved verification files:")
print(f"   - data/exports/verification_complete_mismatches.csv ({len(mismatches)} cases)")
print(f"   - data/exports/verification_partial_matches.csv ({len(partial)} cases)")
print(f"   - data/exports/verification_low_consensus.csv ({len(low_consensus)} cases)")
print("=" * 80)
