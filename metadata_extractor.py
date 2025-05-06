import fitz  # PyMuPDF
import re
import pdfplumber
import requests
from PyPDF2 import PdfReader


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
            "producer": raw.get("producer")
        })
    except Exception:
        pass
    return meta


def extract_metadata_pypdf2(pdf_path):
    """
    Extract metadata with PyPDF2: title, author, subject, keywords.
    """
    meta = {"title": None, "author": None, "subject": None, "keywords": None}
    try:
        reader = PdfReader(pdf_path)
        info = reader.metadata
        meta.update({
            "title": getattr(info, 'title', None),
            "author": getattr(info, 'author', None),
            "subject": getattr(info, 'subject', None),
            "keywords": getattr(info, 'keywords', None)
        })
    except Exception:
        pass
    return meta


def scrape_header_footer(pdf_path):
    """
    Scan first 3 and last 3 pages for "Journal, Vol X, Issue Y" pattern.
    """
    pattern = re.compile(
        r"(?P<journal>[A-Za-z &\-:]+),?\s*Vol(?:ume)?\.?\s*(?P<volume>\d+),?\s*Iss(?:ue)?\.?\s*(?P<issue>\d+)",
        re.IGNORECASE
    )
    journal = volume = issue = None
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages[:3] + pdf.pages[-3:]
        for page in pages:
            text = page.extract_text() or ""
            m = pattern.search(text)
            if m:
                journal = m.group("journal").strip()
                volume  = m.group("volume")
                issue   = m.group("issue")
                break
    return {"journal": journal, "volume": volume, "issue": issue}


def extract_doi(pdf_path):
    """
    Extract DOI from first 3 pages via regex.
    """
    doi = None
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:3]:
            text = page.extract_text() or ""
            m = re.search(r"10\.\d{4,9}/[^\s]+", text)
            if m:
                doi = m.group(0)
                break
    return doi


def crossref_lookup(doi):
    """
    Query Crossref for metadata given a DOI.
    """
    try:
        headers = {"User-Agent": "SearchBuddy/1.0 (mailto:todd@miamioh.edu)"}
        resp = requests.get(f"https://api.crossref.org/works/{doi}", headers=headers, timeout=10)
        msg = resp.json().get("message", {})
        return {
            "journal": msg.get("container-title", [None])[0],
            "volume": msg.get("volume"),
            "issue": msg.get("issue"),
            "author": "; ".join([a.get("family","") for a in msg.get("author",[])])
        }
    except Exception:
        return {}


def crossref_lookup_by_title(title):
    """
    Query Crossref’s bibliographic endpoint for the given title.
    Returns dict with keys journal, volume, issue, author.
    """
    result = {}
    try:
        if not title:
            return result
        from urllib.parse import quote_plus
        q = quote_plus(title)
        url = f"https://api.crossref.org/works?query.bibliographic={q}&rows=1"
        headers = {"User-Agent": "SearchBuddy/1.0 (mailto:todd@miamioh.edu)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        if not items:
            return result
        msg = items[0]
        result["journal"] = msg.get("container-title", [None])[0]
        result["volume"]  = msg.get("volume")
        result["issue"]   = msg.get("issue")
        authors = msg.get("author", [])
        result["author"] = "; ".join([f"{a.get('given','')} {a.get('family','')}".strip() for a in authors])
    except Exception:
        pass
    return result


def extract_metadata(pdf_path):
    """
    Master metadata extractor: embedded -> PyPDF2 -> header/footer -> DOI -> title-search.
    Returns merged metadata dict.
    """
    meta = extract_metadata_pymupdf(pdf_path)
    if not meta.get("title") or not meta.get("author"):
        fallback = extract_metadata_pypdf2(pdf_path)
        for k, v in fallback.items():
            if not meta.get(k) and v:
                meta[k] = v
    if not meta.get("journal") or not meta.get("volume"):
        hdr = scrape_header_footer(pdf_path)
        for k in ("journal", "volume", "issue"):
            if not meta.get(k) and hdr.get(k):
                meta[k] = hdr[k]
    if not meta.get("journal") or not meta.get("volume") or not meta.get("author"):
        doi = extract_doi(pdf_path)
        if doi:
            cr = crossref_lookup(doi)
            for k, v in cr.items():
                if not meta.get(k) and v:
                    meta[k] = v
    # Title-search fallback
    if not meta.get("journal") or not meta.get("volume") or not meta.get("author"):
        title_cr = crossref_lookup_by_title(meta.get("title", ""))
        for k in ("journal", "volume", "issue", "author"):
            if not meta.get(k) and title_cr.get(k):
                meta[k] = title_cr[k]
    return meta
