import sys
import os
import csv  # ✅ Add to your imports at the top
import shutil
import re
import json
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QLabel, QLineEdit, QRadioButton, QHBoxLayout, QProgressBar
)
from PySide6.QtCore import Qt, QSettings
from PyPDF2 import PdfReader
from metadata_extractor import extract_metadata
import openai

# ✅ DEFAULT PROMPT
PROMPT = (
    "In each academic article, identify a positionality statement where the authors describe their personal identity, background, experiences, assumptions, or biases. "
    "Provide the statement verbatim if present; if none is present, state 'No positionality statement found.'"
)

class PDFExtractorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Search Buddy GUI")
        self.resize(600, 700)

        # Folder selection
        self.folder_label = QLabel(os.getcwd())
        self.select_button = QPushButton("Select Folder")
        self.select_button.clicked.connect(self.choose_folder)

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
        self.progress.setValue(0)

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
        folder = QFileDialog.getExistingDirectory(self, "Select PDF Folder")
        if folder:
            self.folder_label.setText(folder)

    def run_extraction(self):
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

            pdfs = [f for f in os.listdir(folder) if f.lower().endswith('.pdf')]
            total = len(pdfs)
            for idx, fname in enumerate(pdfs, start=1):
                pdf_path = os.path.join(folder, fname)
                self.progress.setValue(int(idx/total*100))
                QApplication.processEvents()

                # Extract metadata
                meta = extract_metadata(pdf_path)
                title = meta.get("title", "")
                author = meta.get("author", "")
                creation = meta.get("creation_date", "")
                producer = meta.get("producer", "") if 'producer' in meta else ""
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
    app_qt = QApplication(sys.argv)
    app_qt.setApplicationName("Search Buddy GUI")  # updated application name
    window = PDFExtractorGUI()
    window.show()
    sys.exit(app_qt.exec())
