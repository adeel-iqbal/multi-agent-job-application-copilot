# parser.py — reads uploaded CV file (PDF or DOCX) and extracts raw text
# this is a deterministic node, no LLM needed here, just file parsing

import os                          # for file path and extension handling
import fitz                        # PyMuPDF — for reading PDF files
from docx import Document          # python-docx — for reading DOCX files
from graph.state import AppState   # our shared state


def parse_cv(state: AppState) -> dict:
    """
    Parser node — reads CV file from uploads/ folder and extracts plain text.
    Writes extracted text into state['cv_raw_text'].
    """

    # get the file path stored in state by Chainlit before graph runs
    cv_file_path = state.get("cv_file_path", "")

    # safety check — if no file path found, return empty text
    if not cv_file_path:
        return {"cv_raw_text": "No CV file provided."}

    # get file extension to decide which parser to use
    # os.path.splitext returns ("filename", ".pdf") — we take index 1
    file_extension = os.path.splitext(cv_file_path)[1].lower()

    # --- PDF parsing ---
    if file_extension == ".pdf":

        # open the PDF file using PyMuPDF
        pdf_document = fitz.open(cv_file_path)

        # initialize empty string to collect text from all pages
        extracted_text = ""

        # loop through every page in the PDF
        for page_number in range(len(pdf_document)):

            # get the page object
            page = pdf_document[page_number]

            # extract plain text from this page and add to our string
            extracted_text += page.get_text()

        # close the PDF after reading
        pdf_document.close()

    # --- DOCX parsing ---
    elif file_extension == ".docx":

        # open the DOCX file using python-docx
        docx_document = Document(cv_file_path)

        # each paragraph in docx is a separate object
        # we join all paragraph texts with newline between them
        extracted_text = "\n".join([
            paragraph.text                        # get text of each paragraph
            for paragraph in docx_document.paragraphs  # loop all paragraphs
            if paragraph.text.strip()             # skip empty paragraphs
        ])

    # --- unsupported file type ---
    else:
        extracted_text = f"Unsupported file type: {file_extension}. Please upload PDF or DOCX."

    # return dict — LangGraph merges this into the shared state
    return {"cv_raw_text": extracted_text}