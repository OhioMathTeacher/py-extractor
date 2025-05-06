import sys
import os
import csv
import shutil
import re
import pdfplumber
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QLabel, QLineEdit, QRadioButton, QHBoxLayout, QProgressBar
)
from PySide6.QtCore import Qt, QSettings, QDir
from PyPDF2 import PdfReader
from metadata_extractor import extract_metadata, crossref_lookup
import openai

# Default prompt for positionality extraction
PROMPT = (
    "In each academic article, identify a positionality statement where the authors describe their personal identity, background, experiences, assumptions, or biases. "
    "If present, briefly summarize in one sentence; if none is present, respond 'No positionality statement found.'"
)

# ----------------- Positionality Extraction -----------------
def extract_positionality_from_pdf(pdf_path, custom_prompt):
    try:
        reader = PdfReader(pdf_path)
        full_text = " ".join(page.extract_text() or "" for page in reader.pages)
        snippet = full_text[:5000]
        messages = [
            {"role": "system", "content": (
                "You are an assistant summarizing whether and how an author reflects on their own perspective. "
                "Look for first-person reflections (I, we, my); if found, summarize why that counts as a positionality statement. "
                "If none, say 'No positionality statement found.'"
            )},
            {"role": "user", "content": f"{custom_prompt}\n\n{snippet}"}
        ]
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=100,
            temperature=0.0
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error extracting positionality: {e}"
# ------------------------------------------------------------

class PDFExtractorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Search Buddy GUI")
        self.resize(600, 700)
        self.settings = QSettings("TechnologyEducatorsAlliance", "SearchBuddy")

        # Folder selection
        start_folder = self.settings.value("last_folder", QDir.homePath())
        self.folder_label = QLabel(start_folder)
        self.select_button = QPushButton("Select Folder")
        self.select_button.clicked.connect(self.choose_folder)

        # API Key input
        self.api_label = QLabel("OpenAI API Key:")
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setPlaceholderText("sk-…")
        self.api_input.setText(self.settings.value("openai_api_key", ""))
        self.api_input.editingFinished.connect(
            lambda: self.settings.setValue("openai_api_key", self.api_input.text())
        )

        # Mode radios
        self.keyword_radio = QRadioButton("Keyword Search")
        self.ai_radio = QRadioButton("AI Analysis")
        self.ai_radio.setChecked(True)

        # Prompt input
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(PROMPT)
        self.prompt_input.setFixedHeight(80)

        # Run and progress
        self.run_button = QPushButton("Run Extraction")
        self.run_button.clicked.connect(self.run_extraction)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.status_label = QLabel("Ready")

        # Output and save
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.save_button = QPushButton("Save CSV As…")
        self.save_button.clicked.connect(self.save_csv)
        self.save_button.setEnabled(False)

        # Layout
        hbox = QHBoxLayout()
        hbox.addWidget(self.keyword_radio)
        hbox.addWidget(self.ai_radio)
        layout = QVBoxLayout()
        layout.addWidget(self.folder_label)
        layout.addWidget(self.select_button)
        layout.addWidget(self.api_label)
        layout.addWidget(self.api_input)
        layout.addLayout(hbox)
        layout.addWidget(self.prompt_input)
        layout.addWidget(self.run_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.output)
        layout.addWidget(self.save_button)
        self.setLayout(layout)
        self.last_csv_path = None

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select PDF Folder", self.folder_label.text())
        if folder:
            self.folder_label.setText(folder)
            self.settings.setValue("last_folder", folder)

    def run_extraction(self):
        openai.api_key = self.api_input.text().strip()
        folder = self.folder_label.text()
        if not os.path.isdir(folder):
            self.status_label.setText("Please select a valid folder.")
            return

        fields = ["Filename","Title","Author","Journal","Volume","Issue","Found","Statement","Rationale"]
        csv_path = os.path.join(folder, "output.csv")
        self.last_csv_path = csv_path

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

            pdfs = [p for p in os.listdir(folder) if p.lower().endswith('.pdf')]
            total = len(pdfs)
            found_count = 0

            for i, fname in enumerate(pdfs, start=1):
                pct = int(i / total * 100)
                self.progress.setValue(pct)
                self.progress.setFormat(f"{pct}%")
                self.status_label.setText(f"{pct}%")
                QApplication.processEvents()

                path = os.path.join(folder, fname)
                meta = extract_metadata(path)

                # Crossref fallback
                if meta.get("title"):
                    try:
                        cr = crossref_lookup(meta["title"])
                        meta["journal"] = meta.get("journal") or (cr.get("container-title") or [""])[0]
                        meta["volume"]  = meta.get("volume")  or cr.get("volume", "")
                        meta["issue"]   = meta.get("issue")   or cr.get("issue", "")
                        if not meta.get("author") and cr.get("author"):
                            names = [f"{a.get('given','')} {a.get('family','')}".strip() for a in cr["author"]]
                            meta["author"] = "; ".join(names)
                    except:
                        pass

                                # Positionality detection
                if self.keyword_radio.isChecked():
                    text = " ".join(page.extract_text() or "" for page in PdfReader(path).pages)
                    # Look for first-person reflections
                    m = re.search(r"(I|we).*?\.", text)
                    found = bool(m)
                    stmt = m.group(0) if found else ""
                    rationale = (
                        "Found a first‑person sentence via regex keyword match."
                        if found else
                        "No first‑person sentence matched via regex."
                    )
                else:
                    summary = extract_positionality_from_pdf(path, self.prompt_input.toPlainText() or PROMPT)
                    if summary.startswith("No positionality statement found"):
                        found = False
                        stmt = ""
                        rationale = "AI scan and regex fallback found no positionality statement."
                    else:
                        found = True
                        stmt = summary
                        rationale = "Used AI to generate a one‑sentence summary of the author’s positionality."

                if found:
                    found_count += 1

                # Write CSV row
                writer.writerow({
                    "Filename":   fname,
                    "Title":      meta.get("title",""),
                    "Author":     meta.get("author",""),
                    "Journal":    meta.get("journal",""),
                    "Volume":     meta.get("volume",""),
                    "Issue":      meta.get("issue",""),
                    "Found":      "Yes" if found else "No",
                    "Statement":  stmt,
                    "Rationale":  rationale
                })

                # Update GUI log
                if found:
                    self.output.append(f"✅ {fname} – {stmt} ({rationale})")
                else:
                    self.output.append(f"❌ {fname} – No positionality statement found. ({rationale})")

            # Final summary
            self.output.append("")
            self.output.append(f"🔄 Extraction complete: {found_count}/{total} statements found. CSV saved to {csv_path}")

        self.save_button.setEnabled(True)
        self.status_label.setText("Completed")

    def save_csv(self):
        dest, _ = QFileDialog.getSaveFileName(self, "Save CSV", filter="CSV Files (*.csv)")
        if dest:
            try:
                shutil.copy(self.last_csv_path, dest)
                self.status_label.setText(f"CSV saved to {dest}")
            except Exception as e:
                self.status_label.setText(f"Error saving CSV: {e}")

if __name__ == '__main__':
    print("🍎 Starting Search Buddy GUI…")
    app = QApplication(sys.argv)
    window = PDFExtractorGUI()
    window.show()
    print("🎉 GUI shown, entering event loop")
    sys.exit(app.exec())
