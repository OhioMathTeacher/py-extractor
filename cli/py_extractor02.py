import os
import csv
import re
import fitz  # PyMuPDF for PDF reading
import openai  # OpenAI API

def extract_metadata(text):
    lead_author_first = "N/A"
    lead_author_last = "N/A"
    journal_title = "N/A"
    volume = "N/A"
    issue = "N/A"
    month_year = "N/A"
    doi = "N/A"

    doi_match = re.search(r'DOI:\s*(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', text, re.I)
    if doi_match:
        doi = f"https://doi.org/{doi_match.group(1)}"

    journal_match = re.search(r'(Educational Researcher|Journal of [\w\s]+|Review of [\w\s]+)', text)
    if journal_match:
        journal_title = journal_match.group(1)

    vol_issue_match = re.search(r'Vol\.\s*(\d+)\s*No\.\s*(\d+)', text)
    if vol_issue_match:
        volume = vol_issue_match.group(1)
        issue = vol_issue_match.group(2)

    month_year_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December).*\d{4}', text, re.I)
    if month_year_match:
        month_year = month_year_match.group(0)

    author_match = re.search(r'([A-Z][a-z]+)\s+([A-Z][a-z]+)', text)
    if author_match:
        lead_author_first = author_match.group(1)
        lead_author_last = author_match.group(2)

    return lead_author_first, lead_author_last, journal_title, volume, issue, month_year, doi

def search_for_keywords(text, keywords):
    text_lower = text.lower()
    for keyword in keywords:
        if keyword.lower() in text_lower:
            snippet_start = text_lower.find(keyword.lower())
            snippet = text[max(0, snippet_start-30):snippet_start+100]
            return "Yes", snippet.strip()
    return "No", ""

def search_with_ai(text, api_key, model, user_prompt):
    """
    Uses OpenAI API to determine if an article matches the user's detection prompt.
    Returns ('Yes', snippet) or ('No', '').
    """
    openai.api_key = api_key

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an academic assistant helping to detect specific content in research articles."},
                {"role": "user", "content": f"{user_prompt}\n\nHere is the article text:\n{text[:12000]}"}  # Limit to ~12,000 characters
            ],
            temperature=0.2,
            max_tokens=500
        )

        reply = response.choices[0].message.content.strip()

        if "yes" in reply.lower():
            return "Yes", reply
        elif "no" in reply.lower():
            return "No", reply
        else:
            return "Unclear", reply

    except Exception as e:
        print(f"⚠️ OpenAI API call failed: {e}")
        return "Error", str(e)

def process_pdfs(input_folder, output_csv, mode, api_key=None, provider=None, model=None, user_prompt=None):
    """
    Processes PDFs in a folder using either keyword search or AI-based analysis.
    """
    search_keywords = ["positionality", "standpoint", "identity", "reflexivity"]
    data_rows = []

    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(input_folder, filename)
            text = ""

            try:
                doc = fitz.open(pdf_path)
                for page in doc:
                    text += page.get_text()
            except Exception as e:
                print(f"⚠️ Failed to read {filename}: {e}")
                continue

            if mode == "keyword":
                found, snippet = search_for_keywords(text, search_keywords)
            elif mode == "ai":
                found, snippet = search_with_ai(text, api_key, model, user_prompt)
            else:
                found, snippet = "Error", "Unknown mode selected"

            lead_first, lead_last, journal, volume, issue, month_year, doi = extract_metadata(text)

            row = [
                filename,
                lead_first,
                lead_last,
                journal,
                volume,
                issue,
                month_year,
                doi,
                found,
                snippet,
                ""
            ]
            data_rows.append(row)

    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Filename", "Lead Author First Name", "Lead Author Last Name", "Journal Title", "Volume", "Issue", "Month/Year", "DOI", "Detected Positionality Statement?", "Snippet/Excerpt", "Notes"])
        writer.writerows(data_rows)

    print(f"✅ Finished processing. Results saved to {output_csv}")

if __name__ == "__main__":
    # Defaults
    default_input_folder = "~/pdfs"
    default_output_filename = "output.csv"
    default_provider = "openai"
    default_model = "gpt-4o"
    default_detection_prompt = "Does this article contain an explicit positionality statement by the author? Provide an excerpt if so."

    print("=== Article Scanner Version 0.2 ===")
    print("Press ENTER to accept the default value shown in [brackets].\n")

    # Folder and output file setup
    input_folder = input(f"Enter the folder path containing the PDFs [{default_input_folder}]: ") or default_input_folder
    input_folder = os.path.expanduser(input_folder)

    if not os.path.isdir(input_folder):
        print(f"❌ Error: The folder '{input_folder}' does not exist.")
        exit(1)

    output_filename = input(f"Enter desired output CSV filename (including .csv) [{default_output_filename}]: ") or default_output_filename
    output_path = os.path.join(os.getcwd(), output_filename)

    # Mode selection
    mode = input("Enter mode [keyword, ai]: ") or "keyword"

    api_key = None
    provider = None
    model = None
    user_prompt = None

    if mode.lower() == "ai":
        api_key = input("Enter your API key (leave blank to return to keyword mode): ").strip()
        if not api_key:
            print("⚠️ No API key provided. Falling back to keyword mode.\n")
            mode = "keyword"
        else:
            provider = input(f"Enter LLM provider [{default_provider}]: ") or default_provider
            model = input(f"Enter model name [{default_model}]: ") or default_model

            if provider.lower() != "openai":
                print(f"⚠️ Support for {provider} is not available yet. Falling back to keyword mode.\n")
                mode = "keyword"
                api_key = None
                provider = None
                model = None
            else:
                user_prompt = input("\nEnter a description of what you want the AI to detect (or press ENTER to use the default prompt):\n") or default_detection_prompt

    # Final settings summary
    print("\n=== Settings Summary ===")
    print(f"Input folder: {input_folder}")
    print(f"Output file: {output_path}")
    print(f"Mode: {mode}")
    if mode == "ai":
        print(f"Provider: {provider}")
        print(f"Model: {model}")
        print(f"Detection prompt: {user_prompt}")
    print("\nStarting processing...\n")

    # Call the main processing function
    process_pdfs(input_folder, output_path, mode, api_key, provider, model, user_prompt)
