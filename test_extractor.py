import os
import re
from metadata_extractor import extract_metadata

# Pass 2: Keyword proximity settings
KEYWORDS = {"positionality", "reflexive", "bias", "identity", "subjectivity", "standpoint", "reflexivity"}
WINDOW_SIZE = 125    # number of words
MIN_HITS = 2        # minimum keywords in window to flag


def find_proximity_hits(text, window_size=WINDOW_SIZE, min_hits=MIN_HITS):
    """
    Return list of (start_idx, end_idx) word positions where
    at least `min_hits` keywords occur within `window_size` words.
    """
    words = re.findall(r"\w+", text)
    positions = [i for i, w in enumerate(words) if w.lower() in KEYWORDS]
    hits = []
    left = 0
    for right in range(len(positions)):
        # advance left bound to maintain window size
        while positions[right] - positions[left] > window_size:
            left += 1
        if right - left + 1 >= min_hits:
            hits.append((positions[left], positions[right]))
    # merge overlapping regions
    merged = []
    for start, end in sorted(hits):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged


def extract_snippets(words, regions, window=10):
    """
    Given word list and regions [(s,e)], return text snippets around each region.
    """
    snippets = []
    for start, end in regions:
        s = max(0, start - window)
        e = min(len(words), end + window)
        snippet = " ".join(words[s:e])
        snippets.append(snippet)
    return snippets


def test_extractor(root_dir):
    """
    Walk through all PDF files in root_dir, extract metadata,
    apply proximity check, and report results.
    """
    for fname in os.listdir(root_dir):
        if not fname.lower().endswith('.pdf'):
            continue
        full_path = os.path.join(root_dir, fname)
        metadata = extract_metadata(full_path)
        text = metadata.get('text', '')
        # new proximity pass
        regions = find_proximity_hits(text)
        words = re.findall(r"\w+", text)
        snippets = extract_snippets(words, regions)
        # output
        print(f"{fname} → proximity hits: {len(snippets)}")
        for snip in snippets:
            print(f"    ...{snip}...")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Test positionality proximity on PDFs'
    )
    parser.add_argument(
        'root_dir', help='Directory containing PDF files to test'
    )
    args = parser.parse_args()
    test_extractor(args.root_dir)
