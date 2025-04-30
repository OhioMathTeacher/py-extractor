import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QLabel, QLineEdit
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

# ✅ REAL PDF READER LOGIC — place this RIGHT BELOW the DEFAULT_PROMPT
from PyPDF2 import PdfReader
import openai

# Set your API key here (optionally load from env or config for production)
openai.api_key = "your-api-key-here"

def get_ai_summary(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that identifies and summarizes positionality statements in academic articles."},
                {"role": "user", "content": f"Summarize the positionality statement (if any) in the following article:

{text}"}
            ],
            max_tokens=300,
            temperature=0.5,
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"[Error calling OpenAI API: {e}]"

def extract_positionality_from_pdf(pdf_path, custom_prompt):
    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() or ""

        if not full_text.strip():
            return f"[{os.path.basename(pdf_path)}] No readable text found.\n"

        # For now, just preview first 500 characters
        preview = full_text[:500].strip().replace("\n", " ")
        return f"[{os.path.basename(pdf_path)}]\n{preview}...\n\n"

    except Exception as e:
        return f"[{os.path.basename(pdf_path)}] Error reading file: {e}\n"


class PDFExtractorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("py-extractor")
        self.setGeometry(100, 100, 600, 500)

        layout = QVBoxLayout()

        # Directory label
        self.dir_label = QLabel("No folder selected.")
        layout.addWidget(self.dir_label)

        # Select folder button
        self.dir_button = QPushButton("Select Folder")
        self.dir_button.clicked.connect(self.select_folder)
        layout.addWidget(self.dir_button)

        # Prompt input
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter custom prompt (or leave blank for default)")
        layout.addWidget(self.prompt_input)

        # Run button
        self.run_button = QPushButton("Run Extraction")
        self.run_button.clicked.connect(self.run_extraction)
        layout.addWidget(self.run_button)

        # Output text box
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)

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

        prompt = self.prompt_input.text().strip() or DEFAULT_PROMPT
        output_text = ""

        # ✅ Loop through all PDFs in selected directory
        for filename in os.listdir(self.selected_directory):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(self.selected_directory, filename)
                output_text += extract_positionality_from_pdf(pdf_path, prompt)
                output_text += "\n"

        if output_text.strip():
            self.output_box.setPlainText(output_text)
        else:
            self.output_box.setPlainText("No PDF files found in the selected folder.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFExtractorGUI()
    window.show()
    sys.exit(app.exec())
