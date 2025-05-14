import os
import fitz  # PyMuPDF
import re
import pdfplumber
import requests
from PyPDF2 import PdfReader
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
            text = "".join(page.extract_text() or "" for page in pdf.pages[:2])
        match = re.search(r"^Title:\s*(.*)$", text, re.MULTILINE)
        if match: meta["title"] = match.group(1).strip()
        match = re.search(r"^Author[s]?:\s*(.*)$", text, re.MULTILINE)
        if match: meta["author"] = match.group(1).strip()
        match = re.search(r"doi:\s*(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", text, re.IGNORECASE)
        if match: meta["doi"] = match.group(1)
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
        if match: return match.group(0)
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
    Multi-strategy positionality detection with GPT fallback and scoring.
    Returns dict: matched_tests, snippets, score.
    """
    # compile footer matcher to stop at page‐footer lines
    footer_re = re.compile(r"^HSR\s+\d+", re.IGNORECASE)

    # grab the 1–2 pages before the References section
    with pdfplumber.open(pdf_path) as pdf:
        ref_page = None
        for i, pg in enumerate(pdf.pages):
            text_pg = pg.extract_text() or ""
            if re.search(r"^\s*References\s*$", text_pg, re.IGNORECASE | re.MULTILINE):
                ref_page = i
                break
        start = ref_page - 2 if ref_page and ref_page >= 2 else max(len(pdf.pages) - 2, 0)
        end   = ref_page or len(pdf.pages)
        pos_text = "\n".join(
            pdf.pages[j].extract_text() or ""
            for j in range(start, end)
        )

    # 1) Regex‐based quick tests
    tests = {
        "explicit_positionality":    re.compile(r"\b(?:My|Our) positionality\b", re.IGNORECASE),
        "first_person_reflexivity":  re.compile(r"\bI\s+(?:reflect|acknowledge|consider|recognize)\b", re.IGNORECASE),
        "researcher_self":           re.compile(r"\bI,?\s*as a researcher,", re.IGNORECASE),
        "author_self":               re.compile(r"\bI,?\s*as (?:the )?author,", re.IGNORECASE),
        "as_a_role":                 re.compile(r"\bAs a [A-Z][a-z]+(?: [A-Z][a-z]+)*,\s*I\b", re.IGNORECASE),
    }
    matched, snippets = [], {}
    for name, pat in tests.items():
        m = pat.search(pos_text)
        if m:
            matched.append(name)
            snippets[name] = m.group(0).strip()

    # 2) Header‐based extraction, confined to pos_text, capped by lines & chars
    lines = pos_text.splitlines()
    MAX_LINES = 10
    MAX_CHARS = 500
    for hdr in ("Positionality", "Reflexivity", "Researcher Background"):
        pat = re.compile(rf"^\s*{hdr}\b", re.IGNORECASE | re.MULTILINE)
        if pat.search(pos_text):
            paragraph = []
            for idx, line in enumerate(lines):
                if pat.match(line):
                    # collect subsequent non-blank, non-footer lines
                    for nxt in lines[idx+1:]:
                        if not nxt.strip() or footer_re.match(nxt):
                            break
                        paragraph.append(nxt.strip())
                        if len(paragraph) >= MAX_LINES:
                            break
                    break
            snippet = " ".join(paragraph)
            if len(snippet) > MAX_CHARS:
                # truncate to last full word under char cap
                snippet = snippet[:MAX_CHARS].rsplit(" ", 1)[0] + "…"
            if snippet:
                matched.append("header")
                snippets["header"] = snippet
            break

    # 3) GPT fallback for low-confidence cases
    score_partial = len(matched) / (len(tests) + 1)  # regex + header
    api_key = getattr(openai, "api_key", None) or os.getenv("OPENAI_API_KEY")
    if score_partial < 0.2 and api_key:
        openai.api_key = api_key
        try:
            prompt = (
                "Extract the author's positionality or reflexivity statement "
                "from the text below. If none exists, reply 'NONE':\n\n"
                + pos_text
            )
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            gpt_snip = resp.choices[0].message.content.strip()
            if gpt_snip.upper() != "NONE":
                matched.append("gpt_fallback")
                snippets["gpt_fallback"] = gpt_snip
        except Exception as e:
            print(f"GPT fallback error: {e}")
    elif score_partial < 0.2:
        print("Skipping GPT fallback: OPENAI_API_KEY not set")

    # Final positionality confidence score (includes GPT)
    score = len(matched) / (len(tests) + 2)
    return {"matched_tests": matched, "snippets": snippets, "score": score}

def extract_metadata(pdf_path):
    meta = {}
    meta.update(extract_metadata_pymupdf(pdf_path))
    text_meta = extract_metadata_pdfplumber(pdf_path)
    meta.update(text_meta)

    if meta.get("doi"): meta["doi"] = meta["doi"].strip().rstrip('.;,')
    if not meta.get("doi"):
        doi = extract_doi(pdf_path)
        if doi: meta["doi"] = doi.strip().rstrip('.;,')

    if meta.get("doi"):
        cr = crossref_lookup(meta["doi"]) or datacite_lookup(meta["doi"])
        for k, v in cr.items():
            if not meta.get(k) and v: meta[k] = v

    title_for_lookup = text_meta.get("title")
    if title_for_lookup:
        cr2 = crossref_lookup(title_for_lookup)
        for k in ("journal","volume","issue","author"):
            if not meta.get(k) and cr2.get(k): meta[k] = cr2[k]

    if not meta.get("author"):
        base = os.path.basename(pdf_path)
        nm = os.path.splitext(base)[0]
        m = re.match(r"^([A-Za-z]+)(?:-et-al)?(?:-\d{4}.*)?$", nm)
        if m:
            lead = m.group(1).replace("-"," ").title()
            auth = f"{lead} et al." if "-et-al" in nm else lead
            meta["author"] = auth
            meta["author_from_filename"] = auth

    pos = extract_positionality(pdf_path)
    meta["positionality_tests"] = pos.get("matched_tests")
    meta["positionality_snippets"] = pos.get("snippets")
    meta["positionality_score"] = pos.get("score")
    sc = meta.get("positionality_score",0)
    meta["positionality_confidence"] = "high" if sc>=0.75 else "medium" if sc>=0.2 else "low"
    return meta
