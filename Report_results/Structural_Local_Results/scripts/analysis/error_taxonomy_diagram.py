"""Generate error taxonomy visualization with CORRECT labels"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (18, 6)

# Define base directory
base_dir = Path(__file__).parent.parent.parent

# Load data
detailed = pd.read_csv(base_dir / "data" / "exports" / "multi_label_only_detailed.csv")

# CORRECTED error taxonomy (matching your actual labels)
error_taxonomy = {
    'A': {'type': 'Loop Condition', 'category': 'Control Flow'},
    'B': {'type': 'Condition Branch', 'category': 'Control Flow'},
    'C': {'type': 'Statement Integrity', 'category': 'Code Structure'},
    'D': {'type': 'Output/Input Format', 'category': 'I/O Operations'},
    'E': {'type': 'Variable Initialization', 'category': 'Data Handling'},
    'F': {'type': 'Data Type', 'category': 'Data Handling'},
    'G': {'type': 'Computation', 'category': 'Operations'},
    'NONE': {'type': 'No Error', 'category': 'No Error'}
}

# Count predictions by label
label_counts = {}
for _, row in detailed.iterrows():
    labels = row['pred_labels'].split(',') if row['pred_labels'] else []
    for label in labels:
        label = label.strip()
        if label:
            label_counts[label] = label_counts.get(label, 0) + 1

print("="*80)
print("📊 ERROR DISTRIBUTION ANALYSIS")
print("="*80)
print("\nLabel Frequencies:")
for label in sorted(label_counts.keys()):
    cat = error_taxonomy.get(label, {}).get('category', 'Unknown')
    type_name = error_taxonomy.get(label, {}).get('type', 'Unknown')
    count = label_counts[label]
    print(f"  {label}: {count:4d} ({type_name:25s} - {cat})")

# Create figure with 3 subplots
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

# === LEFT: Error Taxonomy ===
categories = {
    'Control Flow': ['A', 'B'],
    'Code Structure': ['C'],
    'I/O Operations': ['D'],
    'Data Handling': ['E', 'F'],
    'Operations': ['G'],
    'No Error': ['NONE']
}

hierarchy_data = []
for cat, labels in categories.items():
    for label in labels:
        desc = error_taxonomy.get(label, {}).get('type', 'Unknown')
        count = label_counts.get(label, 0)
        hierarchy_data.append({
            'Category': cat,
            'Label': label,
            'Description': desc,
            'Count': count
        })

hierarchy_df = pd.DataFrame(hierarchy_data)

# Sort and plot
hierarchy_df_sorted = hierarchy_df.sort_values('Count', ascending=True)
colors = plt.cm.Set3(range(len(categories)))
cat_colors = {cat: colors[i] for i, cat in enumerate(categories.keys())}

bars = ax1.barh(
    hierarchy_df_sorted['Label'], 
    hierarchy_df_sorted['Count'],
    color=[cat_colors[cat] for cat in hierarchy_df_sorted['Category']]
)

ax1.set_xlabel('Prediction Frequency', fontsize=12, fontweight='bold')
ax1.set_ylabel('Error Label', fontsize=12, fontweight='bold')
ax1.set_title('Error Taxonomy & Distribution', fontsize=14, fontweight='bold')
ax1.grid(axis='x', alpha=0.3)

# Add value labels
for i, (idx, row) in enumerate(hierarchy_df_sorted.iterrows()):
    ax1.text(row['Count'] + 5, i, str(row['Count']), va='center', fontsize=9)

# Add legend
legend_elements = [plt.Rectangle((0,0),1,1, fc=cat_colors[cat], label=cat) 
                   for cat in categories.keys()]
ax1.legend(handles=legend_elements, loc='lower right', fontsize=8)

# === MIDDLE: Model Performance (All 4 Metrics) ===
model_metrics = detailed.groupby('model').agg({
    'case_a_precision': 'mean',
    'case_b_recall': 'mean',
    'case_c_any_overlap': 'mean',
    'case_d_jaccard': 'mean'
}).round(3)

x = range(len(model_metrics))
width = 0.2

ax2.bar([i - 1.5*width for i in x], model_metrics['case_a_precision'], width, 
        label='Case A (Precision)', alpha=0.8, color='#1f77b4')
ax2.bar([i - 0.5*width for i in x], model_metrics['case_b_recall'], width, 
        label='Case B (Recall)', alpha=0.8, color='#ff7f0e')
ax2.bar([i + 0.5*width for i in x], model_metrics['case_c_any_overlap'], width, 
        label='Case C (Any)', alpha=0.8, color='#2ca02c')
ax2.bar([i + 1.5*width for i in x], model_metrics['case_d_jaccard'], width, 
        label='Case D (Jaccard)', alpha=0.8, color='#d62728')

ax2.set_xlabel('Model', fontsize=12, fontweight='bold')
ax2.set_ylabel('Score', fontsize=12, fontweight='bold')
ax2.set_title('All 4 Metrics by Model', fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels([m.replace('_', '-').replace('anthropic-', '').replace('openai-', '').replace('google-', '') 
                      for m in model_metrics.index], rotation=45, ha='right', fontsize=8)
ax2.legend(loc='upper left', fontsize=9)
ax2.grid(axis='y', alpha=0.3)
ax2.set_ylim(0, 1.0)

# === RIGHT: Jaccard Score Comparison ===
jaccard_summary = detailed.groupby('model')['case_d_jaccard'].mean().sort_values(ascending=True)
model_labels = [m.replace('_', '-').replace('anthropic-', '').replace('openai-', '').replace('google-', '') 
                for m in jaccard_summary.index]

bars = ax3.barh(model_labels, jaccard_summary.values, color='steelblue', alpha=0.8)

# Color best model differently
best_idx = len(jaccard_summary) - 1
bars[best_idx].set_color('gold')
bars[best_idx].set_alpha(1.0)

ax3.set_xlabel('Jaccard Score (Mean)', fontsize=12, fontweight='bold')
ax3.set_ylabel('Model', fontsize=12, fontweight='bold')
ax3.set_title('Model Ranking (Jaccard Score)', fontsize=14, fontweight='bold')
ax3.grid(axis='x', alpha=0.3)
ax3.set_xlim(0, 0.7)

# Add value labels
for i, v in enumerate(jaccard_summary.values):
    ax3.text(v + 0.01, i, f'{v:.3f}', va='center', fontsize=10, fontweight='bold')

plt.tight_layout()
output_file = base_dir / 'data' / 'exports' / 'error_taxonomy_diagram.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✓ Saved: {output_file}")
plt.show()
