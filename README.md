# 🧠 Search Buddy (`py-extractor`)

Extract **targeted content** from PDFs using AI or keyword search — via a simple **GUI** or **CLI**.

Originally built for large-scale qualitative research in educational scholarship, this Python app now includes a full-featured graphical interface for:

- 🧑‍🏫 Positionality statement detection  
- 📄 Metadata & DOI extraction  
- 📤 CSV export with live debug tracking

> 🚀 **[Latest Release: v0.3.5](https://github.com/Technology-Educators-Alliance/py-extractor/releases/latest)** — with improved debug output and one-click CSV download.

> ⚠️ **Known Issue:** This version still needs work on the search routines. For example, the positionality statement in `dean-2017-identity-negotiation.pdf` is not currently being detected by v0.3.5.

---

## 🧰 Quick Setup (GUI)

### 1. Clone the repo

```bash
git clone https://github.com/Technology-Educators-Alliance/py-extractor.git
cd py-extractor
```

### 2. Create and Activate a Virtual Environment

Create the environment (same for all platforms):

```bash
python3 -m venv venv
```

Then activate it:

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
source venv/bin/activate
```

</details>

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
.\venv\Scripts\Activate.ps1
```

</details>


### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the GUI

```bash
python gui_openai_05_06_25v5.py
```

**Features:**

- 🔑 Enter OpenAI API key (masked)
- 📁 Choose a folder of PDFs
- 🟢 Click **Run Extraction**
- 🧾 Follow the debug output as it runs
- 🧃 Click **Download CSV** when done!

---

## 💻 Command-Line Interface (CLI)

For power users and scripting workflows:

```bash
cd cli
python py_extractor02v2.py /path/to/your/pdfs --mode ai
```

Use `--help` for options:

```bash
python py_extractor02v2.py --help
```

---

## 📦 Key Files

| File | Purpose |
|------|---------|
| `gui_openai_05_06_25v5.py` | Main GUI with OpenAI + debug + CSV |
| `metadata_extractor.py` | Shared helper for extracting headers, footers, metadata, DOIs |
| `requirements.txt` | Dependencies: PySide6, PyMuPDF, pdfplumber, etc. |
| `cli/py_extractor02v2.py` | CLI version for headless/automated use |
| `setup_instructions.md` | One-page guide for quick onboarding |

---

## 🪪 License

Licensed under **CC BY-NC 4.0**  
For non-commercial, educational use only.  
See [LICENSE.txt](LICENSE.txt) for full details.

---

Happy extracting! 🧙‍♂️📚🔍
