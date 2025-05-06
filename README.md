# Search Buddy (py-extractor)

**Extract targeted content from PDFs using AI or keyword search via a simple GUI (or a CLI).**

Originally designed for large-scale qualitative research in educational scholarship, this tool now features a full Python GUI for positionality and metadata extraction.

---

## 🚀 Quick Setup (GUI)

1. **Clone the repo**

   ```bash
   git clone https://github.com/Technology-Educators-Alliance/py-extractor.git
   cd py-extractor
   ```

2. **Create & activate a clean Python virtualenv**

   ```bash
   python3 -m venv venv
   # macOS/Linux
   source venv/bin/activate
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Run the GUI**

   ```bash
   python gui_openai_05_06_25v3.py
   ```

   * Paste your OpenAI API Key into the **API Key** field (password‑masked).
   * Select your PDF folder.
   * Click **Run Extraction** and watch the `%` update in the status bar.
   * When finished, `output.csv` will appear in your PDF folder.

---

## 🖥️ Command‑Line Interface (CLI)

If you prefer terminal pros:

```bash
# Navigate into the CLI folder
cd cli

# Run the original Python script
python py_extractor02v2.py /path/to/your/pdfs --mode ai
```

Use `--help` for full options:

```bash
python py_extractor02v2.py --help
```

---

## 🧰 What’s Inside

* **`gui_openai_05_06_25v3.py`**
  The current GUI launcher with:

  * Persistent folder & API‑Key storage via QSettings
  * AI‑supported positionality extraction (GPT‑4O) + regex fallback
  * Metadata pipeline (PyMuPDF → PyPDF2 → pdfplumber header/footer → Crossref)

* **`metadata_extractor.py`**
  Central helper module:

  * `extract_metadata(pdf_path)` including embedded‑metadata, header/footer scraping, DOI/Crossref lookup.

* **`setup_instructions.md`**
  A < 30‑minute quickstart guide for any laptop.

* **`requirements.txt`**
  Lists all Python dependencies:

  ```
  PySide6
  pymupdf
  PyPDF2
  pdfplumber
  requests
  openai
  ```

* **`cli/py_extractor02v2.py`**
  Legacy CLI script for headless environments.

---

## 📄 License

This project is licensed **CC BY‑NC 4.0** for **non‑commercial, educational** use only. See [LICENSE.txt](LICENSE.txt) for details.

*Happy extracting!* 🧙‍♂️
