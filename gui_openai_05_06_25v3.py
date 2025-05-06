import sys
import os
import csv  # ✅ Add to your imports at the top
import shutil
import re
import json
import pdfplumber
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QLabel, QLineEdit, QRadioButton, QHBoxLayout, QProgressBar
)
from PySide6.QtCore import Qt, QSettings, QDir
from PyPDF2 import PdfReader
from metadata_extractor import extract_metadata
import openai

# ✅ DEFAULT PROMPT
PROMPT = (
    "In each academic article, identify a positionality statement where the authors describe their personal identity, background, experiences, assumptions, or biases. "
    "Provide the statement verbatim if present; if none is present, state 'No positionality statement found.'"
)

# — Positionality Extraction Function —
def extract_positionality_from_pdf(pdf_path, custom_prompt):
    """
    Use PDF text and OpenAI to extract a positionality statement.
    """
    try:
        reader = PdfReader(pdf_path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            return f"[{os.path.basename(pdf_path)}] No positionality statement found."
        # Prepare messages
        full_text = text.replace("\n", " ")
        snippet = full_text[:5000]  # expanded window
        messages = [
            {"role": "system", "content": "You are an assistant that extracts positionality statements from academic articles. Look for first-person reflections (I, we)."},
            {"role": "user", "content": f"{custom_prompt}\n\n{snippet}"}
        ]
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.0
        )
        result = resp.choices[0].message.content.strip()
        # Regex fallback
        m = re.search(r"\b[Ii]\s+(?:may|am|caution|argue)[^\.]+\.", full_text)
        if "No positionality statement found" in result and m:
            return m.group(0)
        return result
    except Exception as e:
        return f"[{os.path.basename(pdf_path)}] Error: {e}"

class PDFExtractorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Search Buddy GUI")
        self.resize(600, 700)

        # Persistent settings (with explicit app and org)
        self.settings = QSettings("TechnologyEducatorsAlliance", "SearchBuddy")

        # Folder selection with last-used folder
        start_folder = self.settings.value("last_folder", QDir.homePath())
        self.folder_label = QLabel(start_folder)
        self.select_button = QPushButton("Select Folder")
        self.select_button.clicked.connect(self.choose_folder)

        # — API Key Input —
        self.api_label = QLabel("OpenAI API Key:")
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setPlaceholderText("sk-…")
        self.api_input.setText(self.settings.value("openai_api_key", ""))
        self.api_input.editingFinished.connect(
            lambda: self.settings.setValue("openai_api_key", self.api_input.text())
        )

        # Mode selection
        self.keyword_radio = QRadioButton("Keyword Search")
        self.ai_radio = QRadioButton("AI Analysis")
        self.ai_radio.setChecked(True)

        # Prompt input
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter custom prompt (or blank for default)")

        # Run button
        self.run_button = QPushButton("Run Extraction")
        self.run_button.clicked.connect(self.run_extraction)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        # Use status_label for percentage
        self.progress.setTextVisible(False)

        # Status label
        self.status_label = QLabel("Ready")

        # Output area
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        # Save CSV button
        self.save_button = QPushButton("Save CSV As…")
        self.save_button.clicked.connect(self.save_csv)
        self.save_button.setEnabled(False)

        # Layout
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.keyword_radio)
        hlayout.addWidget(self.ai_radio)

        layout = QVBoxLayout()
        layout.addWidget(self.folder_label)
        layout.addWidget(self.select_button)
        layout.addWidget(self.api_label)
        layout.addWidget(self.api_input)
        layout.addLayout(hlayout)
        layout.addWidget(self.prompt_input)
        layout.addWidget(self.run_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.output)
        layout.addWidget(self.save_button)

        self.setLayout(layout)
        self.last_csv_path = None

    def choose_folder(self):
        # Open dialog at last-used folder
        folder = QFileDialog.getExistingDirectory(
            self, "Select PDF Folder", self.folder_label.text()
        )
        if folder:
            self.folder_label.setText(folder)
            self.settings.setValue("last_folder", folder)

    def run_extraction(self):
        # Apply the API key for this run
        openai.api_key = self.api_input.text().strip()

        folder = self.folder_label.text()
        if not os.path.isdir(folder):
            self.status_label.setText("Please select a valid folder.")
            return

        # Prepare CSV
        csv_path = os.path.join(folder, "output.csv")
        self.last_csv_path = csv_path
        with open(csv_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "Filename", "Title", "Author", "CreationDate", "Producer",
                "Journal", "Volume", "Issue", "Summary"
            ])
            writer.writeheader()

            pdfs = [pdf for pdf in os.listdir(folder) if pdf.lower().endswith('.pdf')]
            total = len(pdfs)
            for idx, fname in enumerate(pdfs, start=1):
                pdf_path = os.path.join(folder, fname)
                percent = int(idx / total * 100)
                self.progress.setValue(percent)
                self.status_label.setText(f"{percent}%")
                QApplication.processEvents()

                # Extract metadata
                meta = extract_metadata(pdf_path)
                title = meta.get("title", "")
                author = meta.get("author", "")
                creation = meta.get("creation_date", "")
                producer = meta.get("producer", "")
                journal = meta.get("journal", "")
                volume = meta.get("volume", "")
                issue = meta.get("issue", "")

                # Extract positionality
                prompt = self.prompt_input.text() or PROMPT
                summary = extract_positionality_from_pdf(pdf_path, prompt)

                # Write row
                writer.writerow({
                    "Filename": fname,
                    "Title": title,
                    "Author": author,
                    "CreationDate": creation,
                    "Producer": producer,
                    "Journal": journal,
                    "Volume": volume,
                    "Issue": issue,
                    "Summary": summary
                })

                # Update output window
                self.output.append(f"{fname}: {summary}\n")

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

if __name__ == "__main__":
    print("🍎 Starting Search Buddy GUI…")
    app_qt = QApplication(sys.argv)
    app_qt.setOrganizationName("TechnologyEducatorsAlliance")
    app_qt.setApplicationName("Search Buddy GUI")
    window = PDFExtractorGUI()
    window.show()
    print("🎉 GUI shown, entering event loop")
    sys.exit(app_qt.exec())
