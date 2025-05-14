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
    Extract text-based metadata using pdfplumber by scanning the first two pages.
    Returns dict: title, author, journal, volume, issue, pages, doi.
    """
    meta = {"title": None, "author": None, "journal": None, "volume": None, "issue": None, "pages": None, "doi": None}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages[:2]:
                text += page.extract_text() or ""
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
    Try extracting DOI by scanning the first two pages.
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
    url = (f"https://api.crossref.org/works/{doi_or_title}" if isinstance(doi_or_title, str) and doi_or_title.startswith("10.") else
           "https://api.crossref.org/works?query.title=" + requests.utils.quote(doi_or_title or ""))
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"Crossref lookup returned status {resp.status_code} for {doi_or_title}")
            return {}
        data = resp.json()
        item = (data["message"]["items"][0] if not doi_or_title.startswith("10.") else data["message"])
        return {
            "journal": item.get("container-title", [None])[0],
            "volume": item.get("volume"),
            "issue": item.get("issue"),
            "author": ", ".join([f"{a.get('given')} {a.get('family')}" for a in item.get("author", [])]) if item.get("author") else None,
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
        author_list = [f"{c.get('givenName', '')} {c.get('familyName', '')}".strip() for c in creators]
        return {
            "journal": attrs.get("container-title"),
            "volume": attrs.get("volume"),
            "issue": attrs.get("issue"),
            "author": ", ".join(author_list) if author_list else None,
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
    ""`


```python
_next steps omitted for brevity`

            if gpt_snip:
        matched.append("gpt_fallback")
        snippets["gpt_fallback"] = gpt_snip

    score = len(matched) / (len(tests) + 2)
    return {"matched_tests": matched, "snippets": snippets, "score": score}


def extract_metadata(pdf_path):
    """
    Master function: combine metadata extraction and positionality scoring.
    Returns dict including positionality_confidence.
    """
    meta = {}
    meta.update(extract_metadata_pymupdf(pdf_path))
    text_meta = extract_metadata_pdfplumber(pdf_path)
    meta.update(text_meta)

    if meta.get("doi"):
        meta["doi"] = meta["doi"].strip().rstrip('.;,')
    if not meta.get("doi"):
        doi = extract_doi(pdf_path)
        if doi:
            meta["doi"] = doi.strip().rstrip('.;,')

    # Crossref lookup
    if meta.get("doi"):
        cr = crossref_lookup(meta["doi"])
        if not cr:
            dc = datacite_lookup(meta["doi"])
            cr = dc
        for k, v in cr.items():
            if not meta.get(k) and v:
                meta[k] = v

    # Additional Crossref by title if needed
    title_for_lookup = text_meta.get("title")
    if title_for_lookup:
        cr2 = crossref_lookup(title_for_lookup)
        for k in ("journal", "volume", "issue", "author"):
            if not meta.get(k) and cr2.get(k):
                meta[k] = cr2[k]

    # Filename-based author fallback
    if not meta.get("author"):
        base = os.path.basename(pdf_path)
        name = os.path.splitext(base)[0]
        m = re.match(r"^([A-Za-z]+)(?:-et-al)?(?:-\d{4}.*)?$", name)
        if m:
            lead = m.group(1).replace("-", " ").title()
            authors = f"{lead} et al." if "-et-al" in name else lead
            meta["author"] = authors
            meta["author_from_filename"] = authors

    pos = extract_positionality(pdf_path)
    meta["positionality_tests"] = pos.get("matched_tests")
    meta["positionality_snippets"] = pos.get("snippets")
    meta["positionality_score"] = pos.get("score")

    score = meta.get("positionality_score", 0)
    if score >= 0.75:
        confidence = "high"
    elif score >= 0.2:
        confidence = "medium"
    else:
        confidence = "low"
    meta["positionality_confidence"] = confidence

    return meta
