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
import openai

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

# --------------- AI Helper Functions ---------------

def get_ai_summary(text, custom_prompt=None):
    if not openai.api_key:
        return "[Error: no API key set]"
    prompt_content = custom_prompt or DEFAULT_PROMPT
    try:
        truncated = text[:5000]
        messages = [
            {"role": "system", "content": "You are an assistant that identifies and summarizes positionality statements."},
            {"role": "user", "content": f"{prompt_content}\n\nArticle text: {truncated}"}
        ]
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=300,
            temperature=0.5
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error calling OpenAI API: {e}]"


def extract_positionality_from_pdf(pdf_path, custom_prompt=None):
    try:
        reader = PdfReader(pdf_path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            return f"[{os.path.basename(pdf_path)}] No readable text."
        snippet = text[:500].replace("\n", " ")
        return snippet + "..."
    except Exception as e:
        return f"[{os.path.basename(pdf_path)}] Error: {e}"


def get_author_name(text):
    if not openai.api_key:
        return ""
    try:
        truncated = text[:1500]
        messages = [
            {"role": "system", "content": "You are an assistant that extracts author names from academic articles. Return a comma-separated list of author names only, with no additional commentary."},
            {"role": "user", "content": f"Extract the author name(s) from this article text and return a comma-separated list ONLY: {truncated}"}
        ]
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=50,
            temperature=0.0
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return ""

# --------------- Metadata Extraction Routines ---------------

def extract_metadata_pdfinfo(pdf_path):
    reader = PdfReader(pdf_path)
    info = reader.metadata or {}
    return {
        "Title": info.get("/Title", ""),
        "Author": info.get("/Author", ""),
        "CreationDate": info.get("/CreationDate", ""),
        "Producer": info.get("/Producer", ""),
        "Journal": "",
        "Volume": "",
        "Issue": ""
    }


def extract_metadata_regex(text):
    meta = {"Journal": "", "Volume": "", "Issue": ""}
    m = re.search(r"^(.*Journal.*?)\s*\|\s*Vol\.?\s*(\d+),\s*No\.?\s*(\d+)", text, re.IGNORECASE | re.MULTILINE)
    if m:
        meta["Journal"] = m.group(1).strip()
        meta["Volume"] = m.group(2)
        meta["Issue"] = m.group(3)
    else:
        jm = re.search(r"Journal[:\s]+([^\n]+)", text, re.IGNORECASE)
        if jm: meta["Journal"] = jm.group(1).strip()
        vm = re.search(r"Volume\s*(\d+)", text, re.IGNORECASE)
        if vm: meta["Volume"] = vm.group(1)
        im = re.search(r"Issue\s*(\d+)", text, re.IGNORECASE)
        if im: meta["Issue"] = im.group(1)
    return meta


def extract_metadata_ai(text):
    if not openai.api_key:
        return {}
    prompt = f"Extract JSON fields: author, journal, volume, issue from this text:\n{text[:1500]}"
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.0
        )
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return {}


def get_pdf_metadata(pdf_path):
    base = extract_metadata_pdfinfo(pdf_path)
    reader = PdfReader(pdf_path)
    first_page = reader.pages[0].extract_text() or ""
    regex_meta = extract_metadata_regex(first_page)
    for key in ["Journal", "Volume", "Issue"]:
        if not base.get(key) and regex_meta.get(key):
            base[key] = regex_meta[key]
    if openai.api_key:
        ai_meta = extract_metadata_ai(first_page)
        for field in ["author", "journal", "volume", "issue"]:
            cap = field.capitalize()
            if not base.get(cap) and ai_meta.get(field):
                base[cap] = ai_meta[field]
    return base

# --------------- GUI Application ---------------

class PDFExtractorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MyCompany", "py-extractor")
        self.last_csv_path = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Search Buddy GUI")  # updated title
        self.setGeometry(100, 100, 600, 750)
        layout = QVBoxLayout()

        last_dir = self.settings.value("last_folder", "")
        self.dir_label = QLabel(last_dir if last_dir else "No folder selected.")
        if last_dir and os.path.isdir(last_dir):
            self.selected_directory = last_dir
        layout.addWidget(self.dir_label)

        self.dir_button = QPushButton("Select Folder")
        self.dir_button.clicked.connect(self.select_folder)
        layout.addWidget(self.dir_button)

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
        saved_key = self.settings.value("api_key", "")
        if saved_key:
            self.key_input.setText(saved_key)
        self.key_input.returnPressed.connect(self.run_extraction)
        layout.addWidget(self.key_input)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter custom prompt (or blank for default)")
        self.prompt_input.returnPressed.connect(self.run_extraction)
        layout.addWidget(self.prompt_input)

        self.run_button = QPushButton("Run Extraction")
        self.run_button.setAutoDefault(True)
        self.run_button.clicked.connect(self.run_extraction)
        layout.addWidget(self.run_button)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

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
            self.settings.setValue("last_folder", dir_path)

    def run_extraction(self):
        if not hasattr(self, 'selected_directory'):
            self.output_box.setPlainText("Please select a folder first.")
            return
        openai.api_key = self.key_input.text().strip()
        self.settings.setValue("api_key", openai.api_key)
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

        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)

        csv_path = os.path.join(self.selected_directory, "output.csv")
        self.last_csv_path = csv_path

        with open(csv_path, "w", newline='', encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Filename", "Title", "Author", "Journal", "Volume", "Issue", "CreationDate", "Producer", "Summary"])

            for idx, filename in enumerate(pdf_files, 1):
                self.status_label.setText(f"Processing {idx}/{total} ({idx*100//total}%)")
                QApplication.processEvents()
                self.progress_bar.setValue(idx)

                pdf_path = os.path.join(self.selected_directory, filename)
                meta = get_pdf_metadata(pdf_path)
                try:
                    full_text = "".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)
                    author = meta['Author'] or (get_author_name(full_text) if self.ai_radio.isChecked() else "")
                    if self.keyword_radio.isChecked():
                        summary = extract_positionality_from_pdf(pdf_path)
                    else:
                        summary = get_ai_summary(full_text, prompt)

                    line = (
                        f"{filename}:\n"
                        f"  Title: {meta['Title']}\n"
                        f"  Author: {author}\n"
                        f"  Journal: {meta['Journal']}\n"
                        f"  Volume: {meta['Volume']}\n"
                        f"  Issue: {meta['Issue']}\n"
                        f"  CreationDate: {meta['CreationDate']}\n"
                        f"  Producer: {meta['Producer']}\n"
                        f"Summary: {summary}\n\n"
                    )
                    output_text += line
                    writer.writerow([filename, meta['Title'], author, meta['Journal'], meta['Volume'], meta['Issue'], meta['CreationDate'], meta['Producer'], summary])
                except Exception as e:
                    error_msg = f"{filename}: Error - {e}\n"
                    output_text += error_msg
                    writer.writerow([filename, "", "", "", "", "", "", "", error_msg.strip()])

        self.output_box.setPlainText(output_text)
        self.status_label.setText("Completed")
        self.save_button.setEnabled(True)

    def save_csv(self):
        if not self.last_csv_path:
            return
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        default_name = os.path.join(desktop, "output.csv")
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV As",
            default_name,
            "CSV Files (*.csv)"
        )
        if dest:
            try:
                shutil.copy(self.last_csv_path, dest)
                self.status_label.setText(f"CSV saved to {dest}" )
            except Exception as e:
                self.status_label.setText(f"Error saving CSV: {e}")

if __name__ == "__main__":
    app_qt = QApplication(sys.argv)
    app_qt.setApplicationName("Search Buddy GUI")  # Set menu bar app title
    window = PDFExtractorGUI()
    window.show()
    sys.exit(app_qt.exec())
