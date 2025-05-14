# 🧠 Search Buddy (`py-extractor`)

Extract **targeted content** from PDFs using AI or keyword search — via a simple **GUI** or **CLI**.

Originally built for large-scale qualitative research in educational scholarship, this Python app now includes a full-featured graphical interface for:

- 🧑‍🏫 Positionality statement detection  
- 📄 Metadata & DOI extraction  
- 📄 CSV export with live debug tracking

> 🚀 **Latest Release: v0.3.6** — persistent API key, improved prompt UX, and smarter CSV behavior  
> 🔬 **Note:** Positionality detection is improving, but not all PDFs yield matches yet.

---

## 🧰 Quick Setup (GUI)

### 1. Clone or Update the Repo

```bash
git clone https://github.com/Technology-Educators-Alliance/py-extractor.git
cd py-extractor
```

Or update:

```bash
git pull origin main
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv venv
```

Activate it:

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

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the GUI

```bash
python gui_openai_05_13_25v2.py
```

**Features:**

- 🔑 Optional: Enter your OpenAI API key (stored securely)
- 📁 Choose a folder of PDFs
- 🟢 Click **Run Extraction**
- 🧾 Watch live debug output
- 🧃 Click **Download CSV** when complete

---

## 💻 Command-Line Interface (CLI)

For scripting and power users:

```bash
cd cli
python py_extractor02v2.py /path/to/your/pdfs --mode ai
```

Use `--help` for options:

```bash
python py_extractor02v2.py --help
```

---

## 📆 Key Files

| File | Purpose |
|------|---------|
| `gui_openai_05_13_25v2.py` | Current GUI interface (OpenAI optional) |
| `metadata_extractor.py` | Header/footer/metadata/DOI utilities |
| `requirements.txt` | All required dependencies |
| `cli/py_extractor02v2.py` | Command-line version for batch jobs |
| `test_extractor.py` | Smoke tests for GUI behavior |

---

## 📟 Changelog

- **v0.3.6** (May 13, 2025): Persist API key, improve prompt UX, disable download when results are empty
- **v0.3.5** (Archived): Debug output refinements

---

## 🔭 Planned Features

- Save/load settings between sessions
- Drag-and-drop file interface
- Inline preview of extracted content
- Improved AI prompt targeting for positionality

---

## 🧪 License

Licensed under **CC BY-NC 4.0**  
For non-commercial, educational use only.  
See [LICENSE.txt](LICENSE.txt) for full terms.

---

Happy extracting! 🧙‍♂️📚🔍
