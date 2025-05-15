import os
import fitz  # PyMuPDF
import re
import pdfplumber
import requests
from PyPDF2 import PdfReader
from openai import OpenAI
client = OpenAI()


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

import re
import pdfplumber
import openai  # make sure your key is configured

def extract_positionality(pdf_path):
    """
    Extract positionality/reflexivity statements via regex + GPT header fallback + tail scan + conditional GPT-4 full-text pass.
    Returns dict with keys: positionality_tests (list), positionality_snippets (dict), positionality_score (float).
    """
    matched = []
    snippets = {}
    score = 0.0

    # 1) Header regex tests (first page)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = pdf.pages
            header_text = pages[0].extract_text() or ""
    except Exception:
        header_text = ""

    tests = {
        "explicit_positionality":   re.compile(r"\b(?:My|Our) positionality\b", re.IGNORECASE),
        "first_person_reflexivity": re.compile(r"\bI\s+(?:reflect|acknowledge|consider|recognize)\b", re.IGNORECASE),
        "researcher_self":          re.compile(r"\bI,?\s*as a researcher,", re.IGNORECASE),
        "author_self":              re.compile(r"\bI,?\s*as (?:the )?author,", re.IGNORECASE),
        "as_a_role":                re.compile(r"\bAs a [A-Z][a-z]+(?: [A-Z][a-z]+)*,\s*I\b", re.IGNORECASE),
        "I_position":               re.compile(r"\bI\s+(?:position|situat)\b", re.IGNORECASE),
        "I_situated":               re.compile(r"\bI\s+situat\w*\b", re.IGNORECASE),
        "positionality":            re.compile(r"\bpositionalit\w*\b", re.IGNORECASE),
        "self_reflexivity":         re.compile(r"\bI\s+(?:reflect|reflective|reflexiv)\w*\b", re.IGNORECASE),

    }

    for name, pat in tests.items():
        m = pat.search(header_text)
        if m:
            matched.append(name)
            snippets[name] = m.group(0).strip()
            break

    # 2) GPT-fallback on header if no regex hit
    if not matched and header_text:
        snippet = header_text[:500]
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a specialist in academic research methods. "
                        "Find sentences where the author explicitly uses first‑person language "
                        "to reflect on their own positionality or biases. "
                        "If none exists in the passage, reply 'NONE'."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "Passage:\n\n" + header_text[:500]
                    )
                }
            ],
            temperature=0.0
        )

        answer = resp.choices[0].message.content.strip()
        if answer.upper() != "NONE":
            matched.append("gpt_header")
            snippets["gpt_header"] = answer

    # 3) Tail-end regex scan (last 2 pages)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            tail_text = "\n".join(p.extract_text() or "" for p in pdf.pages[-2:])
    except Exception:
        tail_text = ""

    tail_hits = [name for name, pat in tests.items() if pat.search(tail_text)]
    if tail_hits:
        for name in tail_hits:
            if name not in matched:
                matched.append(name)
            snippets.setdefault("tail_"+name, tail_text[:200] + "...")
        score = max(score, 0.5)

    # 4) Baseline score
    if score == 0.0:
        score = len(matched) / (len(tests) + 2)

    # 5) Conditional full-text GPT-4 pass
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
            page_count = len(pdf.pages)
    except Exception:
        full_text = ""
        page_count = 0

    # after computing `score` and loading full_text…

    # only invoke full‐text GPT if:
    # 1) there was some regex/tail signal (score ≥ 0.1)
    # 2) and the PDF actually has a Discussion/Implications/Conclusion heading
    needs_ai = (
        score >= 0.1
        and bool(re.search(r"\b(Discussion|Implications|Conclusion)\b",
                           full_text,
                           re.IGNORECASE))
    )

    if needs_ai:
        m = re.search(r"(Discussion|Implications|Conclusion)", full_text, re.IGNORECASE)
        tail = full_text[m.start():] if m else full_text
        words = tail.split()
        chunk_size = 500
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a specialist in academic research methods. "
                            "Identify any first‑person (‘I’ or ‘we’) statements in this passage "
                            "where the author Reflects on their own positionality or standpoint. "
                            "If none exists, reply 'NO'."
                        )
                    },
                    {
                        "role": "user",
                        "content": "Passage:\n\n" + chunk
                    }
                ],
                temperature=0
            )
            answer = resp.choices[0].message.content.strip()
            if answer.upper().startswith("YES"):
                matched.append("gpt_full_text")
                snippet = answer.splitlines()[1] if "\n" in answer else answer
                snippets["gpt_full_text"] = snippet
                score = 1.0
                break

    return {
        "positionality_tests": matched,
        "positionality_snippets": snippets,
        "positionality_score": score
    }


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
    sc = meta.get("positionality_score", 0.0) or 0.0
    meta["positionality_confidence"] = "high" if sc>=0.75 else "medium" if sc>=0.2 else "low"
    return meta
