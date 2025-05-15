#!/usr/bin/env python3
import os
import sys
from metadata_extractor import extract_metadata

def main():
    # Expect a PDF file or directory as argument
    if len(sys.argv) < 2:
        print("Usage: test_extractor.py <pdf_or_directory>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    # Build list of files to process
    if os.path.isfile(path):
        papers = [path]
    elif os.path.isdir(path):
        papers = [
            os.path.join(path, fn)
            for fn in sorted(os.listdir(path))
            if fn.lower().endswith('.pdf')
        ]
    else:
        print(f"ERROR: Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    # Process each PDF
    for pdf_path in papers:
        fname = os.path.basename(pdf_path)
        try:
            meta = extract_metadata(pdf_path)

            author = meta.get('author')
            file_author = meta.get('author_from_filename')
            score = meta.get('positionality_score', 0)
            tests = meta.get('positionality_tests', [])

            header_snip = meta.get('positionality_snippets', {}).get('header')
            gpt_snip = meta.get('positionality_snippets', {}).get('gpt_fallback')

            # Print results
            print(
                f"{fname} → author: {author!r}"
                + (f"  (from filename: {file_author!r})" if file_author else "")
                + f", score: {score:.2f}, tests: {tests}"
            )
            print("  header snippet:", repr(header_snip))
            print("  GPT snippet   :", repr(gpt_snip))
            print('-' * 80)
        except Exception as e:
            print(f"ERROR on {fname}: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()
