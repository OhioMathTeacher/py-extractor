import os
from metadata_extractor import extract_metadata

PDF_DIR = os.path.expanduser("~/pdfs")
FILENAMES = ("datnow.pdf", "henrekson.pdf", "cycyk.pdf", "dean.pdf")

for fname in FILENAMES:
    path = os.path.join(PDF_DIR, fname)
    meta = extract_metadata(path)
    score = meta.get("positionality_score", 0)
    tests = meta.get("positionality_tests", [])
    print(f"{fname} → score: {score:.2f}, tests: {tests}")
