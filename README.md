# Logical Error Taxonomy Benchmark (Yaksh Evaluation Pipeline)

## Overview

This project evaluates multiple Large Language Models (LLMs) on their ability to detect logical errors in Python programs using structured taxonomies.

The system performs automated benchmarking across multiple logical-error taxonomies using deterministic prompting and multi-iteration evaluation. Results are saved incrementally and execution can safely resume after interruption.

The pipeline is designed for research-grade reproducibility, large batch evaluation, and comparative model analysis.

---

## Features

- Multi-model evaluation via OpenRouter
- Three independent logical-error taxonomies
- Single-label and multi-label classification modes
- Automatic retry and exponential backoff
- Model auto-disable on failure or credit exhaustion
- Incremental checkpoint saving
- Resume-safe execution
- Deterministic outputs (temperature = 0)
- Excel-based dataset and results storage

---

## Supported Models

Configured models:

- anthropic/claude-4.5-sonnet
- google/gemini-2.5-flash
- openai/gpt-5.2
- deepseek/deepseek-v3.2
- qwen/qwen3-coder
- openai/gpt-oss-120b

Models are accessed through OpenRouter.

---

## Logical Error Taxonomies

The benchmark evaluates models under three independent taxonomies:

### 1. CG (Conceptual-Global taxonomy)

Focuses on logical reasoning and algorithm correctness.

### 2. SL (Structural-Local taxonomy)

Focuses on programming structure errors such as loops, functions, and conditions.

### 3. PG (Pedagogical-Granular taxonomy)

Focuses on syntactic logic structure and computation mistakes.

Each taxonomy is evaluated in two modes:

- Single dominant error
- Multi-label error detection

Total evaluation passes:

```
6 iterations
```

---

## Project Structure

```
fosse-iitb/
│
├──Result_report/
├── requirements.txt
├── main.py
├── yaksh_100_que.xlsx
└── README.md
```

---

## Dataset Format

Input Excel file must contain:

| Column Name           | Description         |
| --------------------- | ------------------- |
| question__description | Problem description |
| answer                | Python code         |

---


## Environment Setup

Create a `.env` file:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

Get API key from:
https://openrouter.ai/

---

## Running the Benchmark

```bash
python main.py
```

Execution will:

1. Load dataset
2. Create missing output columns
3. Run all taxonomy iterations
4. Save results after every row

---

## Resume Capability

If execution stops:

- Run the script again.
- Completed rows are skipped automatically.
- Processing resumes safely.

---

## Output File

Results are saved to:

```
yaksh_data/3_iteration_results.xlsx
```

Column naming pattern:

```
<ModelName>_<IterationName>
```

Examples:

```
chat_gpt_iter1_single_CG
gemini_iter2_multi_SL
sonnet_iter1_single_PG
```

Outputs contain:

- Single label (A–J)
- Multiple labels (e.g., B,D,F)
- NONE

---

## Execution Flow

For each iteration:

1. Clean code (remove I/O lines)
2. Construct prompt
3. Query models
4. Sanitize outputs
5. Save predictions
6. Write Excel checkpoint

---

## Failure Handling

The system automatically handles:

- API errors
- Invalid outputs
- Credit exhaustion
- Network interruptions

Failing models are automatically disabled without stopping execution.

---

## Determinism & Reproducibility

The benchmark ensures reproducibility using:

- temperature = 0
- normalized label extraction
- sorted multi-label outputs
- fixed prompts
- incremental saving

For exact environment reproduction:

```bash
pip freeze > requirements_locked.txt
```

---

## Requirements

See `requirements.txt`.

Core libraries:

- pandas
- openai
- python-dotenv
- openpyxl

---

## Troubleshooting

### Excel errors

```bash
pip install openpyxl
```

### Authentication error

Verify `.env` API key.

### Slow execution

Expected due to large number of API calls.

---

## Research Usage

Suitable for:

- LLM reasoning benchmarking
- taxonomy agreement analysis
- model comparison studies
- educational code analysis research

---
