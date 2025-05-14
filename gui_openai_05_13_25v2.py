# Standard library
import sys
import os
import csv
import re
import shutil
from pathlib import Path
from datetime import date, datetime

# Third‑party
import pdfplumber
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QLabel, QLineEdit, QRadioButton, QHBoxLayout,
    QProgressBar, QMessageBox
)
from PySide6.QtGui import QMovie
from PySide6.QtCore import Qt, QSettings, QDir, QSize, QTimer
from PyPDF2 import PdfReader
import openai

# Your code
from metadata_extractor import extract_metadata, crossref_lookup

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

        # persistent settings
        self.settings = QSettings("TechnologyEducatorsAlliance", "SearchBuddy")

        # --- BUILD LAYOUT & WIDGETS ---
        layout = QVBoxLayout()

        # Folder selector
        self.folder_label = QLabel(self.settings.value("last_folder", ""))
        self.select_button = QPushButton("Select Folder")
        self.select_button.clicked.connect(self.choose_folder)
        layout.addWidget(self.folder_label)
        layout.addWidget(self.select_button)

        # API key input
        self.api_label = QLabel("OpenAI API Key:")
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.Password)               # mask input
        self.api_input.setPlaceholderText("sk‑…")                    # hint format
        
        # 🆕 restore last‐used key from settings
        last_key = self.settings.value("openai_api_key", "")
        self.api_input.setText(last_key)        
        
        layout.addWidget(self.api_label)
        layout.addWidget(self.api_input)


        # Search mode radios
        hbox = QHBoxLayout()
        self.keyword_radio = QRadioButton("Keyword Search")
        self.ai_radio      = QRadioButton("AI Analysis")
        self.ai_radio.setChecked(True)
        hbox.addWidget(self.keyword_radio)
        hbox.addWidget(self.ai_radio)
        layout.addLayout(hbox)

        # For the AI prompt box, preload it with your default prompt:
        self.prompt_label = QLabel("Default AI Prompt (type in box to override):")
        layout.addWidget(self.prompt_label)

        default_prompt = (
            "In each academic article, identify a positionality statement where the authors "
            "describe their personal identity, background, experiences, assumptions, or biases. "
            "If present, briefly summarize in one sentence; if none is present, respond ‘No positionality statement found.’"
        )
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(default_prompt)  # ← use placeholder instead
        self.prompt_input.setFixedHeight(80)
        self.prompt_input.setStyleSheet("""
            QTextEdit { color: black; background-color: white;}
            QTextEdit::placeholder { color: #CCCCCC; font-style: italic;}
        """)
        layout.addWidget(self.prompt_input)

        # Run button
        self.run_button = QPushButton("Run Extraction")
        self.run_button.clicked.connect(self.run_extraction)
        layout.addWidget(self.run_button)

        # Progress bar + status label
        self.progress     = QProgressBar()
        self.status_label = QLabel("")
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)

        # Spinner label (emoji‑based)
        #self.spinner_label = QLabel("")
        #layout.addWidget(self.spinner_label)
        #self.spinner_label.hide()

        # Output (debug) window
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        # Save CSV button
        self.save_button = QPushButton("Save CSV As…")
        self.save_button.clicked.connect(self.save_csv)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)

        # finalize
        self.setLayout(layout)

        # --- SPINNER TIMER SETUP ---
        self._spin_frames = ["⏳", ""]
        self._sin_idx    = 0
        self._spin_timer  = QTimer(self)
        self._spin_timer.setInterval(500)
        self._spin_timer.timeout.connect(self._spin)

        # initialise storage
        self.fieldnames   = []
        self.rows         = []

    def _spin(self):
        # flip between hourglass and blank
        self.spinner_label.setText(self._spin_frames[self._spin_idx])
        self._spin_idx = (self._spin_idx + 1) % len(self._spin_frames)

    
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select PDF Folder", self.folder_label.text())
        if folder:
            self.folder_label.setText(folder)
            self.settings.setValue("last_folder", folder)

    def run_extraction(self):
        # –1) wipe debug window so every run starts fresh
        self.output.clear()
        # disable the button so users can’t click twice
        self.run_button.setEnabled(False)
   
        # 0) Grab API key & persist it
        api_key = self.api_input.text().strip()
        openai.api_key = api_key
        self.settings.setValue("openai_api_key", api_key)

        # 0b) get folder
        folder = self.folder_label.text()
        if not os.path.isdir(folder):
            self.status_label.setText("Please select a valid folder.")
            return
    
        # 1) Define CSV fields & init in-memory storage
        fields = [
            "Filename","Title","Author","Journal","Volume","Issue",
            "Found","Statement","Rationale"
        ]
        self.fieldnames = fields
        self.rows = []
    
        # 2) Gather the PDF list and set up counters
        pdfs = [p for p in os.listdir(folder) if p.lower().endswith(".pdf")]
        total = len(pdfs)
        found_count = 0
        
        # — Start the emoji spinner —
        #self.spinner_label.show()
        #self._spin_idx = 0
        #self._spin_timer.start()
    
        # 3) Main loop over each PDF
        for i, fname in enumerate(pdfs, start=1):
            # actual extraction begins here
            path = os.path.join(folder, fname)
            meta = extract_metadata(path)

            # Crossref/DataCite fallback
            if meta.get('title'):
                try:
                    cr = crossref_lookup(meta['title'])
                    for k in ('journal','volume','issue','author'):
                        if not meta.get(k) and cr.get(k):
                            meta[k] = cr[k]
                except:
                    pass

            # Positionality detection
            if self.keyword_radio.isChecked():
                text = " ".join(
                    page.extract_text() or ""
                    for page in PdfReader(path).pages
                )
                m = re.search(r"\b(I|we)\b.*?\.", text)
                found = bool(m)
                stmt = m.group(0) if found else ""
                rationale = (
                    "Found a first-person sentence via regex keyword match."
                    if found else
                    "No first-person sentence matched via regex."
                )
            else:
                summary = extract_positionality_from_pdf(
                    path, self.prompt_input.toPlainText()
                )
                conf = meta.get('positionality_confidence', 'low')
                if meta.get('positionality_tests') and conf in ('medium','high'):
                    found = True
                    stmt = summary
                    rationale = f"Positionality detected (confidence={conf})."
                else:
                    found = False
                    stmt = ""
                    rationale = f"No positionality statement found (confidence={conf})."
            # end of per-PDF logic

    
            # 4) Append to in-memory rows
            self.rows.append({
                "Filename":  fname,
                "Title":     meta.get("title",""),
                "Author":    meta.get("author",""),
                "Journal":   meta.get("journal",""),
                "Volume":    meta.get("volume",""),
                "Issue":     meta.get("issue",""),
                "Found":     "Yes" if found else "No",
                "Statement": stmt,
                "Rationale": rationale,
            })
    
            # 5) Update found counter
            if found:
                found_count += 1
    
            # 6) Update debug log in the GUI
            icon = "✅" if found else "❌"
            self.output.append(f"{icon} {fname} – {rationale}")
    
            # 7) Update progress bar (if not already in your logic)
            pct = int(i / total * 100)
            self.progress.setValue(pct)
            QApplication.processEvents()

    
        # 8) After loop, stop spinner & show final summary
        #self._spin_timer.stop()
        #self.spinner_label.hide()
        self.status_label.setText("Done.")
        self.run_button.setEnabled(True)
        self.output.append("")
        self.output.append(
            f"🔄 Extraction complete: {found_count}/{total} statements found."
        )
        
        # 9) Stop spinner animation
        #self._spin_timer.stop()
        #self.spinner_label.hide()

        # 10) Enable Save button now that we have rows
        self.save_button.setEnabled(True)
        
        # 11) Insert run_button re‑enable here
        self.run_button.setEnabled(True)

    def save_csv(self):
        # Suggest ~/Desktop/positionality_extract_YYYYMMDD_HHMMSS.csv
        desktop = Path.home() / "Desktop"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default = desktop / f"positionality_extract_{ts}.csv"

        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV As",
            str(default),
            "CSV Files (*.csv)"
        )
        if not dest:
            return  # user cancelled

        try:
            with open(dest, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(self.rows)

            self.status_label.setText(f"CSV saved to {dest}")
        except Exception as e:
            self.status_label.setText(f"Error saving CSV: {e}")
            QMessageBox.critical(self, "Save Error", f"Could not save CSV:\n{e}")


if __name__ == '__main__':
    print("🍎 Starting Search Buddy GUI…")
    app = QApplication(sys.argv)
    window = PDFExtractorGUI()
    window.show()
    print("🎉 GUI shown, entering event loop")
    sys.exit(app.exec())
