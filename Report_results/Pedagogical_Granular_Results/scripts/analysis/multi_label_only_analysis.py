"""
Multi-Label Partial Overlap Analysis - CORRECTED VERSION
Only analyzes TRUE multi-label cases (samples with 2+ manual labels)
Calculates 4 metrics: Precision, Recall, Any Overlap, Jaccard Score
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Set

def parse_labels(label_str) -> Set[str]:
    """Parse labels from string, handling brackets, quotes, and commas."""
    if pd.isna(label_str) or str(label_str).strip() == '':
        return set()
    
    # Clean string: remove brackets, quotes, spaces
    cleaned = str(label_str).strip()
    cleaned = cleaned.replace('[', '').replace(']', '').replace("'", "").replace('"', '')
    cleaned = cleaned.replace(' ', '').upper()
    
    # Split by comma
    labels = [label.strip() for label in cleaned.split(',') if label.strip()]
    
    # Filter valid labels only
    valid_labels = set()
    for label in labels:
        if label in {'A','B','C','D','E','F','G','H','NONE'}:
            valid_labels.add(label)
    
    return valid_labels

def calculate_partial_overlap_metrics(pred_labels: Set[str], manual_labels: Set[str]) -> dict:
    """
    Calculate all 4 partial overlap metrics.
    
    Case A (Precision): All predicted labels are in manual labels
    Case B (Recall): All manual labels are in predicted labels
    Case C (Any Overlap): At least one label matches
    Case D (Jaccard): Overlap ratio = |intersection| / |union|
    """
    intersection = pred_labels & manual_labels
    union = pred_labels | manual_labels
    
    # Case A: All predictions are correct (precision-based)
    case_a = 1.0 if len(pred_labels) > 0 and pred_labels.issubset(manual_labels) else 0.0
    
    # Case B: All manual labels captured (recall-based)
    case_b = 1.0 if len(manual_labels) > 0 and manual_labels.issubset(pred_labels) else 0.0
    
    # Case C: Any overlap exists
    case_c = 1.0 if len(intersection) > 0 else 0.0
    
    # Case D: Jaccard similarity score
    case_d = len(intersection) / len(union) if len(union) > 0 else 0.0
    
    return {
        'case_a_precision': case_a,
        'case_b_recall': case_b,
        'case_c_any_overlap': case_c,
        'case_d_jaccard': case_d,
        'intersection_size': len(intersection),
        'pred_size': len(pred_labels),
        'manual_size': len(manual_labels),
        'pred_labels': ','.join(sorted(pred_labels)) if pred_labels else '',
        'manual_labels': ','.join(sorted(manual_labels)) if manual_labels else ''
    }

def parse_result_file(file_path: Path) -> pd.DataFrame:
    """Parse result files with format: sample_id label"""
    predictions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    sample_id = parts[0].strip()
                    pred_labels = ' '.join(parts[1:]).strip()
                    predictions.append({
                        'sample_id': sample_id,
                        'predicted_labels': pred_labels
                    })
        
        return pd.DataFrame(predictions)
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return pd.DataFrame()

def main():
    base_dir = Path(".")
    data_dir = base_dir / "data"
    manual_file = data_dir / "manual_labels" / "manual_labels_cleaned.csv"
    
    print("=" * 80)
    print("🎯 MULTI-LABEL PARTIAL OVERLAP ANALYSIS (CORRECTED)")
    print("=" * 80)
    print("Only analyzes samples where manual labels contain 2+ error types")
    print("=" * 80)
    
    # Load manual labels
    print(f"\n📂 Loading manual labels: {manual_file}")
    try:
        manual_df = pd.read_csv(manual_file)
    except FileNotFoundError:
        print(f"❌ Error: File not found - {manual_file}")
        return
    
    manual_df['sample_id'] = manual_df['Sr. no.'].astype(str)
    manual_df['manual_labels_set'] = manual_df['final_categories'].apply(parse_labels)
    manual_df['label_count'] = manual_df['manual_labels_set'].apply(len)
    
    print(f"✓ Loaded {len(manual_df)} total samples")
    print(f"\n📊 Label Distribution:")
    print(f"   Single-label samples (1 label):  {len(manual_df[manual_df['label_count'] == 1]):3d}")
    print(f"   Multi-label samples (2+ labels): {len(manual_df[manual_df['label_count'] >= 2]):3d}")
    
    # Filter to ONLY multi-label samples
    multi_label_df = manual_df[manual_df['label_count'] >= 2].copy()
    
    if len(multi_label_df) == 0:
        print("\n❌ No multi-label samples found!")
        return
    
    print(f"\n🎯 Analyzing {len(multi_label_df)} multi-label samples only")
    print(f"   (Single-label samples excluded from partial overlap analysis)\n")
    
    all_results = []
    
    # Process ONLY multi-label predictions from both runs
    for run_dir_name in ['results_run1', 'results_run2']:
        run_path = base_dir / run_dir_name
        if not run_path.exists():
            print(f"⚠ Skipping {run_dir_name} - directory not found")
            continue
        
        # ONLY process 'multi' folder
        type_path = run_path / 'multi'
        if not type_path.exists():
            print(f"⚠ Skipping {run_dir_name}/multi - directory not found")
            continue
            
        print(f"📁 Processing {run_dir_name}/multi/")
        
        for result_file in sorted(type_path.glob("*.txt")):
            model_name = result_file.stem.replace('_multi', '')
            print(f"  📄 {model_name:30s}", end=" ")
            
            pred_df = parse_result_file(result_file)
            if pred_df.empty:
                print("→ Empty file")
                continue
            
            pred_df['sample_id'] = pred_df['sample_id'].astype(str)
            pred_df['pred_labels_set'] = pred_df['predicted_labels'].apply(parse_labels)
            
            # Merge ONLY with multi-label samples
            merged = pred_df.merge(
                multi_label_df[['sample_id', 'manual_labels_set']], 
                on='sample_id', 
                how='inner'
            )
            
            if len(merged) == 0:
                print("→ No matching multi-label samples")
                continue
            
            # Calculate metrics for each sample
            metrics_list = []
            for _, row in merged.iterrows():
                metrics = calculate_partial_overlap_metrics(
                    row['pred_labels_set'], 
                    row['manual_labels_set']
                )
                metrics.update({
                    'sample_id': row['sample_id'],
                    'model': model_name,
                    'run': run_dir_name
                })
                metrics_list.append(metrics)
            
            metrics_df = pd.DataFrame(metrics_list)
            all_results.append(metrics_df)
            
            # Print summary stats
            jaccard_mean = metrics_df['case_d_jaccard'].mean()
            case_a_mean = metrics_df['case_a_precision'].mean()
            case_b_mean = metrics_df['case_b_recall'].mean()
            
            print(f"→ {len(metrics_df):3d} samples | Jaccard: {jaccard_mean:.3f} | A: {case_a_mean:.3f} | B: {case_b_mean:.3f}")
    
    if not all_results:
        print("\n❌ No valid results found!")
        return
    
    # Combine all results
    combined_df = pd.concat(all_results, ignore_index=True)
    exports_dir = data_dir / "exports"
    exports_dir.mkdir(exist_ok=True)
    
    # Save detailed results
    detail_file = exports_dir / "multi_label_only_detailed.csv"
    combined_df.to_csv(detail_file, index=False)
    
    # Calculate summary statistics
    summary = combined_df.groupby(['model', 'run']).agg({
        'case_a_precision': ['mean', 'std'],
        'case_b_recall': ['mean', 'std'],
        'case_c_any_overlap': ['mean', 'std'],
        'case_d_jaccard': ['mean', 'std', 'count']
    }).round(4)
    
    summary_file = exports_dir / "multi_label_only_summary.csv"
    summary.to_csv(summary_file)
    
    # Overall summary by model (averaged across runs)
    overall = combined_df.groupby('model').agg({
        'case_a_precision': 'mean',
        'case_b_recall': 'mean',
        'case_c_any_overlap': 'mean',
        'case_d_jaccard': 'mean'
    }).round(4).sort_values('case_d_jaccard', ascending=False)
    
    print("\n" + "=" * 80)
    print("🎯 RESULTS - TRUE MULTI-LABEL CASES ONLY")
    print("=" * 80)
    print("\n📖 Metric Definitions:")
    print("   Case A (Precision): All predicted labels ⊆ manual labels")
    print("   Case B (Recall):    All manual labels ⊆ predicted labels")
    print("   Case C (Any):       Predicted ∩ manual ≠ ∅")
    print("   Case D (Jaccard):   |Predicted ∩ manual| / |Predicted ∪ manual|")
    print("\n📊 OVERALL SUMMARY (averaged across both runs):\n")
    print(overall.to_string())
    
    print("\n" + "=" * 80)
    print(f"💾 Files saved:")
    print(f"   📄 {detail_file}")
    print(f"   📄 {summary_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
