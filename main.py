import pandas as pd
import time
import re
import os
from openai import OpenAI
from dotenv import load_dotenv

# =========================
# CONFIG
# =========================
INPUT_FILE = r"yaksh_data\yaksh_100_que.xlsx"
OUTPUT_FILE = "yaksh_data/combined_yaksh_3_iteration_results.xlsx"

MODELS = {
    "sonnet": "anthropic/claude-4.5-sonnet",
    "gemini": "google/gemini-2.5-flash",
    "chat_gpt": "openai/gpt-5.2",
    "deepseek": "deepseek/deepseek-v3.2",
    "qwen": "qwen/qwen3-coder",
    "gpt_oss": "openai/gpt-oss-120b",
}

MODEL_STATUS = {model_id: "active" for model_id in MODELS.values()}

MAX_RETRIES = 4
BASE_DELAY = 2  # seconds
VALID_OUTPUTS = {"A","B","C","D","E","F","G","H","I","J","NONE"}
# =========================
# LOAD ENV & CLIENT
# =========================
load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# =========================
# LOGICAL ERROR TAXONOMY
# =========================
TAXONOMY_TEXT_har ="""
<taxonomy>
    <category label="A">
        <title>Boundary & Indexing</title>
        <description>Errors in loop bounds or indexing (off-by-one, skipped or extra element).</description>
    </category>
    <category label="B">
        <title>Conditional / Boolean</title>
        <description>Incorrect condition, wrong boolean operator, reversed logic, unreachable branch.</description>
    </category>
    <category label="C">
        <title>State Management</title>
        <description>Incorrect handling of variables across execution (not resetting counters, stale state).</description>
    </category>
    <category label="D">
        <title>Algorithmic Strategy</title>
        <description>Fundamental flaw in approach or data structure; logic does not solve the task.</description>
    </category>
    <category label="E">
        <title>Edge Case Handling</title>
        <description>Fails only on boundary inputs (empty input, single element, zero, negative values).</description>
    </category>
    <category label="F">
        <title>Specification Misunderstanding</title>
        <description>Code does not follow the problem statement, output format, or required function behavior.</description>
    </category>
    <category label="NONE">
        <title>No Error</title>
        <description>No logical error present.</description>
    </category>
</taxonomy>
"""

TAXONOMY_TEXT_yuv = """
<taxonomy>
    <category label="A">
        <title>Input</title>
        <description>Failing to receive all input values or using the incorrect data type for variables.</description>
    </category>
    <category label="B">
        <title>Output</title>
        <description>Non-compliance with required formats or outputting incorrect string literals.</description>
    </category>
    <category label="C">
        <title>Variable</title>
        <description>Storing incorrect values or specifying the wrong data type for a variable.</description>
    </category>
    <category label="D">
        <title>Computation</title>
        <description>Calculating with incorrect values or using the wrong operations.</description>
    </category>
    <category label="E">
        <title>Condition</title>
        <description>Incorrect or insufficient conditional operations in declarations.</description>
    </category>
    <category label="F">
        <title>Branching</title>
        <description>Incorrect program flow (e.g., wrong break placement or if-if instead of if-else).</description>
    </category>
    <category label="G">
        <title>Loop</title>
        <description>Incorrect conditions or variables used in loop declarations.</description>
    </category>
    <category label="H">
        <title>Array/String</title>
        <description>Incorrect initialization or referencing an incorrect index.</description>
    </category>
    <category label="I">
        <title>Function</title>
        <description>Incorrectly defined parameters/return values or wrong arguments in calls.</description>
    </category>
    <category label="J">
        <title>Conceptual</title>
        <description>Solving the wrong problem or missing necessary loops/conditions entirely.</description>
    </category>
    <category label="NONE">
        <title>No Error</title>
        <description>No logical error present.</description>
    </category>
</taxonomy>
"""
TAXONOMY_TEXT_tan = """
<taxonomy>
    <category label="A">
        <title>Loop Condition</title>
        <description>Incorrect loops in the for/while condition.</description>
    </category>

    <category label="B">
        <title>Condition Branch</title>
        <description>Incorrect expression in the if condition.</description>
    </category>

    <category label="C">
        <title>Statement Integrity</title>
        <description>Statement lacks a required part of the logical structure.</description>
    </category>

    <category label="D">
        <title>Output / Input Format</title>
        <description>Incorrect cin/cout or input-output statement.</description>
    </category>

    <category label="E">
        <title>Variable Initialization</title>
        <description>Incorrect declaration or initialization of variables.</description>
    </category>

    <category label="F">
        <title>Data Type</title>
        <description>Incorrect data type used.</description>
    </category>

    <category label="G">
        <title>Computation</title>
        <description>Incorrect basic math operators or calculations.</description>
    </category>

    <category label="NONE">
        <title>No Error</title>
        <description>No logical error present.</description>
    </category>
</taxonomy>

"""

# =========================
# PROMPTS
# =========================
PROMPT_ITER1_SINGLE_har = f"""
You are an expert programming assistant.

Your task:
Identify the SINGLE dominant logical error in the given Python code.

{TAXONOMY_TEXT_har}

Rules:
- Select exactly ONE error type.
- If multiple errors exist, choose the most dominant one.
- If no logical error exists, output ONLY: NONE

Output Rules (STRICT):
- Output exactly ONE label: A B C D E F or NONE
- Do NOT include explanations or extra text.
"""

PROMPT_ITER_MULTI_har = f"""
You are an expert programming assistant.

Your task:
Identify ALL applicable logical error types in the given Python code.

{TAXONOMY_TEXT_har}

Rules:
- Multiple error types may apply.
- Do NOT prioritize or suppress any applicable error.
- If no logical error exists, output ONLY: NONE

Output Rules (STRICT):
- Output comma-separated labels (example: D,F or B,C,E)
- Or output NONE
- Do NOT include explanations or extra text.
"""
PROMPT_ITER1_SINGLE_yuv = f"""
You are an expert programming assistant.

Your task:
Identify the SINGLE dominant logical error in the given Python code.

{TAXONOMY_TEXT_yuv}

Rules:
- Select exactly ONE error type.
- If multiple errors exist, choose the most dominant one.
- If no logical error exists, output ONLY: NONE

Output Rules (STRICT):
- Output exactly ONE label: A B C D E F G H I J or NONE
- Do NOT include explanations or extra text.
"""

PROMPT_ITER_MULTI_yuv = f"""
You are an expert programming assistant.

Your task:
Identify ALL applicable logical error types in the given Python code.

{TAXONOMY_TEXT_yuv}

Rules:
- Multiple error types may apply.
- Do NOT prioritize or suppress any applicable error.
- If no logical error exists, output ONLY: NONE

Output Rules (STRICT):
- Output comma-separated labels (example: D,F or B,C,E)
- Or output NONE
- Do NOT include explanations or extra text.
"""
PROMPT_ITER1_SINGLE_tan = f"""
You are an expert programming assistant.

Your task:
Identify the SINGLE dominant logical error in the given Python code.

{TAXONOMY_TEXT_tan}

Rules:
- Select exactly ONE error type.
- If multiple errors exist, choose the most dominant one.
- If no logical error exists, output ONLY: NONE

Output Rules (STRICT):
- Output exactly ONE label: A B C D E F G or NONE
- Do NOT include explanations or extra text.
"""

PROMPT_ITER_MULTI_tan = f"""
You are an expert programming assistant.

Your task:
Identify ALL applicable logical error types in the given Python code.

{TAXONOMY_TEXT_tan}

Rules:
- Multiple error types may apply.
- Do NOT prioritize or suppress any applicable error.
- If no logical error exists, output ONLY: NONE

Output Rules (STRICT):
- Output comma-separated labels (example: D,F or B,C,E)
- Or output NONE
- Do NOT include explanations or extra text.
"""

ITERATIONS = {
    "iter1_single_harshit": PROMPT_ITER1_SINGLE_har,
    "iter2_multi_harshit": PROMPT_ITER_MULTI_har,
    "iter1_single_yuv": PROMPT_ITER1_SINGLE_yuv,
    "iter2_multi_yuv": PROMPT_ITER_MULTI_yuv,
    "iter1_single_tan": PROMPT_ITER1_SINGLE_tan,
    "iter2_multi_tan": PROMPT_ITER_MULTI_tan,
}

# =========================
# UTILS
# =========================
def sanitize_output(text):
    if text is None:
        return None
    text = text.strip().upper()
    if text == "":
        return None
    match = re.findall(r"\b(A|B|C|D|E|F|G|H|I|J|NONE)\b", text)
    if not match:
        return None
    return ",".join(sorted(set(match))) if len(match) > 1 else match[0]


def clean_code(code: str) -> str:
    lines = code.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("input(", "print(", "open(", "date_input")):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def query_model(model_id, prompt):
    if MODEL_STATUS.get(model_id) != "active":
        return "NONE"

    delay = BASE_DELAY
    empty_count = 0

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )

            if not response or not response.choices:
                raise ValueError("Empty response")

            raw = response.choices[0].message.content
            clean = sanitize_output(raw)

            if clean:
                return clean

            empty_count += 1
            print(f"⚠ Invalid output [{model_id}]: {raw}")

            if empty_count >= 3:
                print(f"❌ Disabling {model_id} (repeated empty output)")
                MODEL_STATUS[model_id] = "disabled"
                return "NONE"

        except Exception as e:
            msg = str(e)
            print(f"⚠ API error [{model_id}] attempt {attempt}: {msg[:120]}")

            if "401" in msg or "402" in msg or "insufficient credits" in msg.lower():
                print(f"❌ Disabling {model_id} (no credits / access)")
                MODEL_STATUS[model_id] = "disabled"
                return "NONE"

            if "NoneType" in msg:
                return "NONE"

        time.sleep(delay)
        delay *= 2

    MODEL_STATUS[model_id] = "disabled"
    return "NONE"
def is_row_complete(df, idx, iter_name):
    for model in MODELS:
        col = f"{model}_{iter_name}"

        val = df.at[idx, col]

        # Treat NaN, empty, or invalid as NOT complete
        if pd.isna(val):
            return False

        val = str(val).strip().upper()
        labels = {x.strip() for x in val.split(",")}
        if not labels.issubset(VALID_OUTPUTS):
            return False

    return True

# =========================
# LOAD / RESUME DATA
# =========================
if os.path.exists(OUTPUT_FILE):
    print(f"📂 Resuming from existing file: {OUTPUT_FILE}")
    df = pd.read_excel(OUTPUT_FILE)
else:
    print("📄 Starting fresh")
    df = pd.read_excel(INPUT_FILE)

required_cols = {"question__description", "answer"}
if not required_cols.issubset(df.columns):
    raise ValueError(f"Missing required columns: {df.columns.tolist()}")

# Ensure output columns exist
for iter_name in ITERATIONS:
    for model in MODELS:
        col = f"{model}_{iter_name}"
        # Create column if missing
        if col not in df.columns:
            df[col] = ""
        # Keep existing values but normalize NaNs safely
        df[col] = df[col].fillna("").astype(str).str.strip()
# Final dataframe cleanup (safe)
df.fillna("", inplace=True)



# =========================
# MAIN EXECUTION (SEQUENTIAL ITERATIONS)
# =========================
for iter_name, prompt_template in ITERATIONS.items():

    print(f"\n===== STARTING {iter_name.upper()} =====")

    for idx, row in df.iterrows():

        # Skip row if already completed for this iteration
        if is_row_complete(df, idx, iter_name):
            continue

        cleaned_code = clean_code(row["answer"])

        full_prompt = f"""
Problem Description:
{row['question__description']}

Python Code:
{cleaned_code}

{prompt_template}
"""

        print(f"▶ Processing row {idx} ({iter_name})")

        for model_name, model_id in MODELS.items():
            col = f"{model_name}_{iter_name}"
            val = df.at[idx, col]
            if not pd.isna(val) and str(val).strip().upper() in VALID_OUTPUTS:
                continue
            pred = query_model(model_id, full_prompt)
            df.at[idx, col] = pred

        # SAVE AFTER EACH ROW
        df.to_excel(OUTPUT_FILE, index=False)
        print(f"✔ Row {idx} saved")

    print(f"✅ Completed {iter_name}")

print("\n🎉 ALL ITERATIONS COMPLETE")
print("Final model status:", MODEL_STATUS)
print(f"Results saved to {OUTPUT_FILE}")
