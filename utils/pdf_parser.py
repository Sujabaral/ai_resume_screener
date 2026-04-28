import fitz

from docx import Document

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(file_path):
    text = ""

    try:
        doc = fitz.open(file_path)

        for page in doc:
            text += page.get_text()

        doc.close()

    except Exception as e:
        print("PDF parsing error:", e)

    return text.strip()