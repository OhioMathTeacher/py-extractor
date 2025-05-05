import os
import json
from PyPDF2 import PdfReader
from gui_openai_patched import (
    extract_metadata_pdfinfo,
    extract_metadata_regex,
    extract_metadata_ai,
)

# ← Change this to your test-PDF folder
TEST_DIR = "/Users/todd/pdfs"

print(f"Testing PDFs in {TEST_DIR}\n")

for fname in sorted(os.listdir(TEST_DIR)):
    if not fname.lower().endswith(".pdf"):
        continue
    path = os.path.join(TEST_DIR, fname)

    # 1) Embedded metadata
    pdfinfo = extract_metadata_pdfinfo(path)

    # 2) Regex on first page
    first_page = PdfReader(path).pages[0].extract_text() or ""
    regex_info = extract_metadata_regex(first_page)

    # 3) AI fallback (only if something’s missing)
    ai_info = {}
    if not pdfinfo.get("Author") or not regex_info.get("Journal"):
        ai_info = extract_metadata_ai(first_page)

    # Merge for display
    combined = {**pdfinfo, **regex_info, **ai_info}

    print(f"--- {fname} ---")
    print(json.dumps(combined, indent=2))
    print()
