#!/usr/bin/env python3
import os
import pandas as pd
from metadata_extractor import extract_positionality

PDF_DIR = os.path.expanduser("~/pdfs")

rows = []
for fn in sorted(os.listdir(PDF_DIR)):
    if not fn.lower().endswith(".pdf"):
        continue
    path = os.path.join(PDF_DIR, fn)
    print(f"Processing {fn}…", flush=True)
    try:
        res = extract_positionality(path)
    except Exception as e:
        print(f"  ⚠️ Error on {fn}: {e!r}", flush=True)
        continue

    score = res.get("positionality_score", 0.0) or 0.0
    tests = res.get("positionality_tests", [])
    expected = "POS" if fn.upper().startswith("POS") else "NEG"

    # tests is the list from res.get("positionality_tests")
    regex_keys = {
        "explicit_positionality", "first_person_reflexivity", "researcher_self",
        "author_self", "as_a_role", "I_position", "I_situated",
        "positionality", "self_reflexivity"
    }

    # did we get any pure‐regex hit?
    has_regex = any(t in regex_keys for t in tests)

    # did we get a GPT‐full‑text hit that we trust?
    has_gpt = "gpt_full_text" in tests and score >= 0.6

    detected = "POS" if (has_regex or has_gpt) else "NEG"

    rows.append({
        "file": fn,
        "expected": expected,
        "detected": detected,
        "score": score,
        "tests": ", ".join(tests),
    })

df = pd.DataFrame(rows)
print("\n✅ Results table:\n")
print(df.to_markdown(index=False))
print("\n🔢 Summary counts:\n")
print(df.groupby(["expected", "detected"])["file"].count())
