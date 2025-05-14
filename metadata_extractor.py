import os
import fitz  # PyMuPDF
import re
import pdfplumber
import requests
from PyPDF2 import PdfReader
# Stub for GPT fallback (requires openai setup)
import openai


def extract_metadata_pymupdf(pdf_path):
    """
    Extract embedded metadata using PyMuPDF (fitz).
    Returns dict: title, author, subject, keywords, creation_date, producer.
    """
    meta = {"title": None, "author": None, "subject": None, "keywords": None, "creation_date": None, "producer": None}
    try:
        doc = fitz.open(pdf_path)
        raw = doc.metadata
        meta.update({
            "title": raw.get("title"),
            "author": raw.get("author"),
            "subject": raw.get("subject"),
            "keywords": raw.get("keywords"),
            "creation_date": raw.get("creationDate"),
            "producer": raw.get("producer"),
        })
    except Exception as e:
        print(f"PyMuPDF metadata extraction failed for {pdf_path}: {e}")
    return meta


def extract_metadata_pdfplumber(pdf_path):
    """
    Extract text-based metadata by scanning the first two pages with pdfplumber.
    Returns dict: title, author, journal, volume, issue, pages, doi.
    """
    meta = {"title": None, "author": None, "journal": None, "volume": None, "issue": None, "pages": None, "doi": None}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "".join(page.extract_text() or "" for page in pdf.pages[:2])
        title_match = re.search(r"^Title:\s*(.*)$", text, re.MULTILINE)
        if title_match:
            meta["title"] = title_match.group(1).strip()
        author_match = re.search(r"^Author[s]?:\s*(.*)$", text, re.MULTILINE)
        if author_match:
            meta["author"] = author_match.group(1).strip()
        doi_match = re.search(r"doi:\s*(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", text, re.IGNORECASE)
        if doi_match:
            meta["doi"] = doi_match.group(1)
    except Exception as e:
        print(f"PdfPlumber metadata extraction failed for {pdf_path}: {e}")
    return meta


def extract_doi(pdf_path):
    """
    Scan the first two pages for a DOI using PyPDF2.
    """
    try:
        reader = PdfReader(pdf_path)
        text = "".join(page.extract_text() or "" for page in reader.pages[:2])
        match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.IGNORECASE)
        if match:
            return match.group(0)
    except Exception as e:
        print(f"PyPDF2 DOI extraction failed for {pdf_path}: {e}")
    return None


def crossref_lookup(doi_or_title):
    """
    Lookup metadata from Crossref using DOI or title.
    Returns dict: journal, volume, issue, author, title.
    """
    headers = {"User-Agent": "py-extractor/0.3 (mailto:youremail@example.com)"}
    if isinstance(doi_or_title, str) and doi_or_title.startswith("10."):
        url = f"https://api.crossref.org/works/{doi_or_title}"
    else:
        url = "https://api.crossref.org/works?query.title=" + requests.utils.quote(doi_or_title or "")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"Crossref lookup returned status {resp.status_code} for {doi_or_title}")
            return {}
        data = resp.json()
        item = data["message"]["items"][0] if not doi_or_title.startswith("10.") else data["message"]
        return {
            "journal": item.get("container-title", [None])[0],
            "volume": item.get("volume"),
            "issue": item.get("issue"),
            "author": ", ".join(f"{a.get('given')} {a.get('family')}" for a in item.get("author", [])) if item.get("author") else None,
            "title": item.get("title", [None])[0],
        }
    except requests.RequestException as e:
        print(f"Crossref lookup network error for {doi_or_title}: {e}")
    except ValueError:
        print(f"Crossref lookup returned invalid JSON for {doi_or_title}")
    return {}


def datacite_lookup(doi):
    """
    Lookup metadata from DataCite using DOI.
    Returns dict: journal, volume, issue, author, title.
    """
    url = f"https://api.datacite.org/works/{doi}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"DataCite lookup returned status {resp.status_code} for {doi}")
            return {}
        data = resp.json()
        attrs = data.get("data", {}).get("attributes", {})
        creators = attrs.get("creator", [])
        authors = ", ".join(f"{c.get('givenName','')} {c.get('familyName','')}".strip() for c in creators)
        return {
            "journal": attrs.get("container-title"),
            "volume": attrs.get("volume"),
            "issue": attrs.get("issue"),
            "author": authors or None,
            "title": attrs.get("title"),
        }
    except requests.RequestException as e:
        print(f"DataCite lookup network error for {doi}: {e}")
    except ValueError:
        print(f"DataCite lookup returned invalid JSON for {doi}")
    return {}


def extract_positionality(pdf_path):
    """
    Multi-strategy positionality detection with scoring.
    Returns dict: matched_tests, snippets, score.
    """
    with pdfplumber.open(pdf_path) as pdf:
        # determine pages before References
        ref_page = None
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if re.search(r"^\s*References\s*$", text, re.IGNORECASE | re.MULTILINE):
                ref_page = i
                break
        start = ref_page - 2 if ref_page and ref_page >= 2 else max(len(pdf.pages)-2, 0)
        end = ref_page if ref_page else len(pdf.pages)
        pos_text = "\n".join(pdf.pages[j].extract_text() or "" for j in range(start, end))
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    tests = {
        "explicit_positionality": re.compile(r"\b(?:My|Our) positionality\b", re.IGNORECASE),
        "first_person_reflexivity": re.compile(r"\bI\s+(?:reflect|acknowledge|consider|recognize)\b", re.IGNORECASE),
        "researcher_self": re.compile(r"\bI,?\s*as a researcher,", re.IGNORECASE),
        "author_self": re.compile(r"\bI,?\s*as (?:the )?author,", re.IGNORECASE),
        "as_a_role": re.compile(r"\bAs a [A-Z][a-z]+(?: [A-Z][a-z]+)*,\s*I\b", re.IGNORECASE),
    }
    matched = []
    snippets = {}
    for name, pattern in tests.items():
        m = pattern.search(pos_text)
        if m:
            matched.append(name)
            snippets[name] = m.group(0).strip()

    # header-based test
    for hdr in ("Positionality", "Reflexivity", "Researcher Background"):
        pat = re.compile(rf"^\s*{hdr}\b", re.IGNORECASE | re.MULTILINE)
        if pat.search(full_text):
            lines = full_text.splitlines()
            for idx, line in enumerate(lines):
                if pat.match(line):
                    for nxt in lines[idx+1:]:
                        if nxt.strip():
                            matched.append("header")
                            snippets["header"] = nxt.strip()
                            break
                    break
            break

    # GPT fallback stub (not yet implemented)
    score = len(matched) / (len(tests) + 2)
    return {"matched_tests": matched, "snippets": snippets, "score": score}


def extract_metadata(pdf_path):
    """
    Combine metadata extraction and positionality scoring.
    Returns dict including positionality_confidence and filename fallback.
    """
    meta = {}
    meta.update(extract_metadata_pymupdf(pdf_path))
    text_meta = extract_metadata_pdfplumber(pdf_path)
    meta.update(text_meta)

    # sanitize and fallback DOI
    if meta.get("doi"): meta["doi"] = meta["doi"].strip().rstrip('.;,')
    if not meta.get("doi"):
        doi = extract_doi(pdf_path)
        if doi: meta["doi"] = doi.strip().rstrip('.;,')

    # Crossref + DataCite lookup
    if meta.get("doi"):
        cr = crossref_lookup(meta["doi"])
        if not cr: cr = datacite_lookup(meta["doi"])
        for k, v in cr.items():
            if not meta.get(k) and v: meta[k] = v

    # title-based Crossref fallback
    title_for_lookup = text_meta.get("title")
    if title_for_lookup:
        cr2 = crossref_lookup(title_for_lookup)
        for k in ("journal","volume","issue","author"):
            if not meta.get(k) and cr2.get(k): meta[k] = cr2[k]

    # filename-based author fallback
    if not meta.get("author"):
        base = os.path.basename(pdf_path)
        name = os.path.splitext(base)[0]
        m = re.match(r"^([A-Za-z]+)(?:-et-al)?(?:-\d{4}.*)?$", name)
        if m:
            lead = m.group(1).replace("-"," ").title()
            auth = f"{lead} et al." if "-et-al" in name else lead
            meta["author"] = auth
            meta["author_from_filename"] = auth

    # positionality scoring
    pos = extract_positionality(pdf_path)
    meta["positionality_tests"] = pos.get("matched_tests")
    meta["positionality_snippets"] = pos.get("snippets")
    meta["positionality_score"] = pos.get("score")
    # confidence bucket
    sc = meta.get("positionality_score",0)
    meta["positionality_confidence"] = ("high" if sc>=0.75 else "medium" if sc>=0.2 else "low")

    return meta