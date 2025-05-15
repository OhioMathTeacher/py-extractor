# 🧠 Search Buddy (`py-extractor`)

Extract **targeted content** from PDFs using **AI analysis** — via a simple **GUI** or **CLI**.

> 🚀 **Latest Release: v0.3.7** — final GUI version, persistent settings, improved metadata mapping, and smoother extraction flow

---

## 🛠 Requirements

* **Python** 3.10 or higher
* **pip** (package installer)

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Key libraries:

* `openai` for AI-powered positionality detection
* `PySide6` for the GUI
* `pdfplumber` & `PyPDF2` for PDF parsing
* `tabulate` for CLI output

---

## 🧰 Quick Setup (GUI)

1. **Clone or update** the repository:

   ```bash
   git clone https://github.com/Technology-Educators-Alliance/py-extractor.git
   cd py-extractor
   # or, if already cloned:
   git pull origin main
   ```

2. **Activate** your Python virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Launch** the GUI:

   ```bash
   python gui_openai_05_15_25v2.py
   ```

4. **Use** the interface:

   * 🔑 Enter or confirm your OpenAI API key (auto‑saved between sessions)
   * 📁 Click **Select Folder** and choose your PDF directory
   * 🟢 Click **Run Extraction** to start processing
   * 🧾 Watch live debug output as each file is processed
   * 🧃 Click **Save CSV As...** (defaults to Desktop with timestamped filename)

---

## 💻 Command-Line Interface (CLI)

Run a quick batch extraction without launching the GUI:

```bash
python scripts/sample_report.py /path/to/pdf/folder
```

This outputs a Markdown-formatted table plus summary counts of detected positionality statements.

---

## 📝 Changelog & Roadmap

* **v0.3.7**: Final GUI layout; removed legacy options; fixed metadata key mapping; real-time progress updates
* **v0.3.6**: Persistent API key; improved prompt UX; smarter CSV defaults

**Upcoming**:

* Batch Dropbox/Drive integration
* Enhanced AI prompt customization

Contributions welcome! Fork, open an issue, or submit a pull request.

---

## 📄 License

Licensed under **CC BY-NC 4.0** (non-commercial educational use). See [LICENSE.txt](LICENSE.txt).
