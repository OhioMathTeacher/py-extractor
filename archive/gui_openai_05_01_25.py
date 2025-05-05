import sys
import os
import csv  # ✅ Add to your imports at the top
import shutil
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QLabel, QLineEdit, QRadioButton, QHBoxLayout
)
from PySide6.QtCore import Qt

# ✅ DEFAULT PROMPT
DEFAULT_PROMPT = (
    "In each academic article, identify a positionality statement — a paragraph or explicit passage "
    "where the author describes aspects of their personal identity, background, experiences, assumptions, "
    "or biases. These statements typically clarify how the author's identity or experiences have influenced "
    "the framing, design, or interpretation of the research. Positionality statements often include explicit "
    "mentions of ethnicity, race, gender, socioeconomic status, educational background, professional role, "
    "or personal connection to the topic. Detect these statements (or confirm their absence) and extract "
    "relevant examples to understand how the author situates themselves within the research context."
)

# ✅ PDF READER AND OPENAI IMPORTS
from PyPDF2 import PdfReader
import openai

# Note: API key will be set at run time; no import-time key check.

def get_ai_summary(text, custom_prompt=None):
    """
    Call OpenAI to summarize positionality statements using either a custom or default prompt.
    """
    if not openai.api_key:
        return "[Error: no API key set]"

    prompt_content = custom_prompt or DEFAULT_PROMPT
    try:
        truncated_text = text[:5000]
        messages = [
            {"role": "system", "content": "You are an assistant that identifies and summarizes positionality statements in academic articles."},
            {"role": "user", "content": f"Summarize the positionality statement (if any) in the following article using this prompt:\n\n{prompt_content}\n\n{text[:2000]}"}
        ]
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=300,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error calling OpenAI API: {e}]"


def get_author_name(text):
    """
    Use OpenAI to extract author name(s) from the article text as a fallback.
    """
    if not openai.api_key:
        return ""
    try:
        truncated = text[:2000]
        messages = [
            {"role": "system", "content": "You are an assistant that extracts the author name(s) from academic article text."},
            {"role": "user", "content": f"Extract the author name(s) from this article text: {truncated}"}
        ]
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=50,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ""


def extract_positionality_from_pdf(pdf_path, custom_prompt=None):
    try:
        reader = PdfReader(pdf_path)
        full_text = "".join(page.extract_text() or "" for page in reader.pages)
        if not full_text.strip():
            return f"[{os.path.basename(pdf_path)}] No readable text found.\n"
        preview = full_text[:500].strip().replace("\n", " ")
        return f"[{os.path.basename(pdf_path)}]\n{preview}...\n\n"
    except Exception as e:
        return f"[{os.path.basename(pdf_path)}] Error reading file: {e}\n"


def get_pdf_metadata(pdf_path):
    """
    Extract metadata fields and parse journal, volume, issue from first page text.
    """
    meta = {"Title": "", "Author": "", "Journal": "", "Volume": "", "Issue": "", "CreationDate": "", "Producer": ""}
    try:
        reader = PdfReader(pdf_path)
        info = reader.metadata or {}
        meta["Title"] = info.get("/Title", "")
        meta["Author"] = info.get("/Author", "")
        meta["CreationDate"] = info.get("/CreationDate", "")
        meta["Producer"] = info.get("/Producer", "")

        # Attempt to parse journal, volume, issue from first page text
        first_page = reader.pages[0].extract_text() or ""
        # Journal name often appears in header or title line
        journal_match = re.search(r"^\s*(?:Journal|Journals?)[:\s]+([^\n]+)", first_page, re.IGNORECASE | re.MULTILINE)
        if journal_match:
            meta["Journal"] = journal_match.group(1).strip()
        # Volume
        vol_match = re.search(r"Volume\s*(\d+)", first_page, re.IGNORECASE)
        if vol_match:
            meta["Volume"] = vol_match.group(1)
        # Issue
        issue_match = re.search(r"Issue\s*(\d+)", first_page, re.IGNORECASE)
        if issue_match:
            meta["Issue"] = issue_match.group(1)
    except Exception:
        pass
    return meta


class PDFExtractorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.last_csv_path = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("py-extractor")
        self.setGeometry(100, 100, 600, 700)
        layout = QVBoxLayout()

        self.dir_label = QLabel("No folder selected.")
        layout.addWidget(self.dir_label)

        self.dir_button = QPushButton("Select Folder")
        self.dir_button.clicked.connect(self.select_folder)
        layout.addWidget(self.dir_button)

        # Mode radio buttons
        mode_layout = QHBoxLayout()
        self.keyword_radio = QRadioButton("Keyword Search")
        self.ai_radio = QRadioButton("AI Analysis")
        self.ai_radio.setChecked(True)
        mode_layout.addWidget(self.keyword_radio)
        mode_layout.addWidget(self.ai_radio)
        layout.addLayout(mode_layout)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Enter OpenAI API key (masked)")
        self.key_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.key_input)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter custom prompt (or blank for default)")
        layout.addWidget(self.prompt_input)

        self.run_button = QPushButton("Run Extraction")
        self.run_button.clicked.connect(self.run_extraction)
        layout.addWidget(self.run_button)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)

        self.save_button = QPushButton("Save CSV As...")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_csv)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def select_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if dir_path:
            self.dir_label.setText(dir_path)
            self.selected_directory = dir_path

    def run_extraction(self):
        if not hasattr(self, 'selected_directory'):
            self.output_box.setPlainText("Please select a folder first.")
            return
        openai.api_key = self.key_input.text().strip()
        if self.ai_radio.isChecked() and not openai.api_key:
            self.output_box.setPlainText("Error: enter OpenAI API key for AI Analysis.")
            return

        prompt = self.prompt_input.text().strip() or DEFAULT_PROMPT
        output_text = ""
        pdf_files = [f for f in os.listdir(self.selected_directory) if f.lower().endswith(".pdf")]
        total = len(pdf_files)
        if total == 0:
            self.output_box.setPlainText("No PDF files found.")
            return

        csv_path = os.path.join(self.selected_directory, "output.csv")
        self.last_csv_path = csv_path

        with open(csv_path, "w", newline='', encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Filename", "Title", "Author", "Journal", "Volume", "Issue", "CreationDate", "Producer", "Summary"])

            for idx, filename in enumerate(pdf_files, 1):
                self.status_label.setText(f"Processing {idx}/{total} ({idx*100//total}%)")
                QApplication.processEvents()
                pdf_path = os.path.join(self.selected_directory, filename)
                meta = get_pdf_metadata(pdf_path)
                try:
                    full_text = "".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)
                    # Determine author: metadata or AI fallback
                    author = meta['Author'] or (get_author_name(full_text) if self.ai_radio.isChecked() else "")
                    # Summarize
                    if self.keyword_radio.isChecked():
                        summary = extract_positionality_from_pdf(pdf_path)
                    else:
                        summary = get_ai_summary(full_text, prompt)

                    output_text += (f"{filename}:\n"
                                    f"  Title: {meta['Title']}\n"
                                    f"  Author: {author}\n"
                                    f"  Journal: {meta['Journal']}\n"
                                    f"  Volume: {meta['Volume']}\n"
                                    f"  Issue: {meta['Issue']}\n"
                                    f"  CreationDate: {meta['CreationDate']}\n"
                                    f"  Producer: {meta['Producer']}\n"
                                    f"Summary: {summary}\n\n")
                    writer.writerow([filename, meta['Title'], author, meta['Journal'], meta['Volume'], meta['Issue'], meta['CreationDate'], meta['Producer'], summary])
                except Exception as e:
                    error_msg = f"{filename}: Error - {e}"
                    output_text += error_msg + "\n"
                    writer.writerow([filename, "", "", "", "", "", "", "", error_msg])

        self.output_box.setPlainText(output_text)
        self.status_label.setText("Completed")
        self.save_button.setEnabled(True)

    def save_csv(self):
        if not self.last_csv_path:
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Save CSV As", "output.csv", "CSV Files (*.csv)")
        if dest:
            try:
                shutil.copy(self.last_csv_path, dest)
                self.status_label.setText(f"CSV saved to {dest}")
            except Exception as e:
                self.status_label.setText(f"Error saving CSV: {e}")

if __name__ == "__main__":
    app_qt = QApplication(sys.argv)
    window = PDFExtractorGUI()
    window.show()
    sys.exit(app_qt.exec())
