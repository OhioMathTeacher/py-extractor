from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QTextEdit, QVBoxLayout, QFileDialog, QProgressBar
)
from PySide6.QtCore import QSettings, Qt
import openai
import sys
import os
import csv
from datetime import datetime
from metadata_extractor import extract_metadata

class PDFExtractorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Search Buddy GUI")
        self.resize(800, 800)

        # persistent settings
        self.settings = QSettings("TechnologyEducatorsAlliance", "SearchBuddy")

        # Main layout
        layout = QVBoxLayout()

        # Folder selector
        self.folder_label = QLabel(self.settings.value("last_folder", ""))
        self.folder_label.setAlignment(Qt.AlignLeft)
        self.select_button = QPushButton("Select Folder")
        self.select_button.clicked.connect(self.choose_folder)
        layout.addWidget(self.folder_label)
        layout.addWidget(self.select_button)

        # OpenAI API key input
        self.api_label = QLabel("OpenAI API Key:")
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setPlaceholderText("sk-…")
        last_key = self.settings.value("openai_api_key", "")
        self.api_input.setText(last_key)
        layout.addWidget(self.api_label)
        layout.addWidget(self.api_input)

        # Default AI Prompt
        self.prompt_label = QLabel("Default AI Prompt (type in box to override):")
        self.prompt_input = QTextEdit()
        self.prompt_input.setFixedHeight(100)
        default_prompt = (
            "In each academic article, identify a positionality statement where the authors describe "
            "their personal identity, background, experiences, assumptions, or biases. If present, "
            "briefly summarize in one sentence; if none is present, respond 'No positionality statement found.'"
        )
        self.prompt_input.setPlainText(default_prompt)
        layout.addWidget(self.prompt_label)
        layout.addWidget(self.prompt_input)

        # Run Extraction button
        self.run_button = QPushButton("Run Extraction")
        self.run_button.clicked.connect(self.run_extraction)
        layout.addWidget(self.run_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Debug output
        self.debug_output = QTextEdit()
        self.debug_output.setReadOnly(True)
        layout.addWidget(self.debug_output)

        # Save CSV button
        self.save_button = QPushButton("Save CSV As...")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_csv)
        layout.addWidget(self.save_button)

        self.setLayout(layout)
        self.save_data = []
        self.results_meta = []

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", self.settings.value("last_folder", "")
        )
        if folder:
            self.settings.setValue("last_folder", folder)
            key = self.api_input.text().strip()
            self.settings.setValue("openai_api_key", key)
            openai.api_key = key
            self.settings.sync()
            self.folder_label.setText(folder)

    def run_extraction(self):
        # disable button to prevent rerun
        self.run_button.setEnabled(False)
        self.run_button.setText("Running...")

        folder = self.settings.value("last_folder", "")
        if not folder or not os.path.isdir(folder):
            self.debug_output.append("Please select a valid folder first.")
            self._finish_run()
            return

        # save and apply API key
        key = self.api_input.text().strip()
        self.settings.setValue("openai_api_key", key)
        openai.api_key = key
        self.settings.sync()

        pdfs = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
        total = len(pdfs)
        found = 0
        self.debug_output.clear()
        self.results_meta.clear()

        for idx, fname in enumerate(pdfs, 1):
            path = os.path.join(folder, fname)
            self.debug_output.append(f"Processing {fname}...")
            meta = extract_metadata(path)
            self.results_meta.append((fname, meta))
            tests = meta.get("positionality_tests", [])
            conf = meta.get("positionality_confidence", "low")
            snippet = ""
            if tests:
                found += 1
                snippets = meta.get("positionality_snippets", {}) or {}
                snippet = snippets.get("gpt_full_text") or snippets.get("header") or snippets.get("tail", "")
                icon = "✅"
                line = f"{icon} {fname} – {snippet} (confidence={conf})"
            else:
                icon = "❌"
                line = f"{icon} {fname} – No positionality statement found (confidence={conf})."
            self.debug_output.append(line)
            self.progress_bar.setValue(int(idx / total * 100))
            QApplication.processEvents()

        self.debug_output.append(f"🔄 Extraction complete: {found}/{total} statements found.")
        QApplication.processEvents()
        self._finish_run()

    def _finish_run(self):
        # Run time summary and prepare data for saving without re-running extractor
        self.save_data = []
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        default_name = datetime.now().strftime("positionality_%Y%m%d_%H%M%S.csv")
        self.save_initial = os.path.join(desktop, default_name)

        for fname, meta in self.results_meta:
            detected = bool(meta.get("positionality_tests"))
            conf = meta.get("positionality_confidence", "low")
            snippet = (meta.get("positionality_snippets", {}) or {}).get("header", "")
            self.save_data.append((fname, detected, conf, snippet))

        # re-enable button
        self.run_button.setText("Run Extraction")
        self.run_button.setEnabled(True)
        # enable save
        self.save_button.setEnabled(bool(self.save_data))

    def save_csv(self):
        if not self.save_data:
            return
        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV",
            getattr(self, 'save_initial', ''),
            "CSV Files (*.csv)"
        )
        if fname:
            with open(fname, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Filename", "Detected", "Confidence", "Snippet"])
                for row in self.save_data:
                    writer.writerow(row)
            self.debug_output.append(f"CSV saved to {fname}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFExtractorGUI()
    window.show()
    sys.exit(app.exec())
