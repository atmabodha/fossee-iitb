# LLM Benchmarking for Python Code Error Detection

A comparative study evaluating six Large Language Models on detecting logical errors in 100 Python programming questions across 8 error categories.

## 📋 Project Overview

**Models Evaluated:**
- **Closed-Source:** Claude Sonnet 4.5, Gemini 2.5 Flash, GPT-5.2
- **Open-Source:** DeepSeek v3.2, Qwen3 Coder, GPT-OSS-120B

**Methodology:**
- 100 Python questions from Yaksh platform
- 8 error categories: Loop Condition (A), Condition Branch (B), Statement Integrity (C), I/O Format (D), Variable Init (E), Data Type (F), Computation (G), None
- 2 independent runs × 2 prompting strategies (single-label, multi-label)
- 24 total configurations per model

## 🎯 Key Findings

### Overall Performance
- **Best Model:** GPT-5.2 (40.5% accuracy), **Best Open-Source:** GPT-OSS-120B (40.0%)
- **Average:** 31.5% across all models (range: 16.75% to 40.5%)
- **Closed-source advantage:** +10% over open-source (36% vs 26%)

### Prompting Strategy Impact
- **Single-label:** 53.3% average | **Multi-label:** 8.7% exact match, 41.0% Jaccard, 83.2% any-overlap
- **Average performance drop:** 44.6% from single to multi-label
- **Surprising finding:** 4 categories (C, D, F, G) perform **better** in multi-label (+13 to +34pp)

### Consistency & Reliability
- **Most consistent:** GPT-5.2 (75.5% run-to-run agreement) | **Least:** DeepSeek (44.5%)
- **Single-label consistency:** 56-85% | **Multi-label:** 33-66% (23pp drop)
- **Agreement quality varies:** Claude 89% correct when consistent vs DeepSeek 50%

### Category-Specific Performance
**Single-label top performers:** None (67.2%), Condition Branch (48.7%), Statement Integrity (48.1%)  
**Multi-label top performers:** Statement Integrity (61.4%), Computation (55.8%), I/O Format (55.6%)

**Multi-label advantage categories:**
- Computation (G): +34.0pp improvement
- I/O Format (D): +33.6pp
- Data Type (F): +21.6pp
- Statement Integrity (C): +13.3pp

**Reason:** Structural errors benefit from multi-label as they naturally co-occur (C+D, C+G, D+G), while semantic errors (E, A) suffer from added complexity.

### Model Agreement & Diversity
- **Highest agreement:** GPT-5.2 & GPT-OSS (66% single-label) - architectural similarity
- **Lowest agreement:** GPT-5.2 & DeepSeek (26% single-label, 18% multi-label)
- **Multi-label consensus collapse:** All model pairs <50% agreement

### Ensemble Performance
- **Single-label:** +3.7% improvement (57.0% vs 53.3%) with 40% clear consensus
- **Multi-label:** +2.3% improvement (11.0% vs 8.7%) with only 1% consensus
- **Limitation:** 58% split decisions in single-label, 87% in multi-label

### Partial Overlap Analysis
- **76pp gap** between exact match (7.2%) and any-overlap (83.2%) reveals models demonstrate partial competence
- **Precision-recall trade-off:** Single-label favors precision (47.8%), multi-label favors recall (66.5%)
- **Jaccard score:** 41.0% average - models typically share ~40% overlap with ground truth


## 🗂️ Repository Structure
```
├── data/
│    ├── exports/           # Analysis outputs & visualizations
│    ├── manual_labels/     # Ground truth annotations
│    ├── processed/         # Cleaned datasets
├── reports/                # Final benchmarking report
├── results_run1/           # First evaluation run
├── results_run2/           # Second evaluation run
├── scripts/                # Analysis scripts
└── README.md
```


## 🔬 Evaluation Metrics

- **Exact Match Accuracy** - All predicted labels match ground truth
- **Precision/Recall/F1** - Per-category performance
- **Jaccard Score** - Multi-label overlap (intersection/union)
- **Pairwise Agreement** - Inter-model similarity
- **Run-to-Run Agreement** - Intra-model consistency


# Conclusion: 
Current LLMs demonstrate partial competence (83.2% partial correctness) but remain unsuitable for autonomous classification (31.5% average accuracy). Models excel at structural pattern recognition but struggle with semantic understanding, showing 48pp performance variation across categories and 44.6pp drop in multi-label mode. The 76pp gap between exact match and partial overlap metrics indicates these models function best as assistive screening tools requiring human oversight, not replacements for expert judgment.
