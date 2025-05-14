import os
from metadata_extractor import extract_metadata

PDF_DIR = os.path.expanduser("~/pdfs")
FILENAMES = ("datnow.pdf", "henrekson.pdf", "cycyk.pdf", "dean.pdf")

for fname in FILENAMES:
    path = os.path.join(PDF_DIR, fname)
    meta = extract_metadata(path)

    author = meta.get("author")
    file_author = meta.get("author_from_filename")
    score = meta.get("positionality_score", 0)
    tests = meta.get("positionality_tests", [])

    header_snip = meta.get("positionality_snippets", {}).get("header")
    gpt_snip    = meta.get("positionality_snippets", {}).get("gpt_fallback")

    print(
        f"{fname} → author: {author!r}"
        + (f"  (from filename: {file_author!r})" if file_author else "")
        + f", score: {score:.2f}, tests: {tests}"
    )
    print("  header snippet:", repr(header_snip))
    print("  GPT snippet   :", repr(gpt_snip))
    print("-" * 80)
