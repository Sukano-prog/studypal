"""
Document loader - Supports TXT, PDF, DOCX
"""

from pathlib import Path
from pypdf import PdfReader
import docx


def load_document(file_path):
    file_path = Path(file_path)
    
    # TXT files
    if file_path.suffix.lower() == '.txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    # PDF files
    elif file_path.suffix.lower() == '.pdf':
        try:
            reader = PdfReader(str(file_path))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            if not pages:
                raise Exception("No text found in PDF")
            return "\n\n".join(pages)
        except Exception as e:
            raise Exception(f"Failed to read PDF: {e}")
    
    # DOCX files
    elif file_path.suffix.lower() == '.docx':
        try:
            doc = docx.Document(str(file_path))
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text.strip())
            if not paragraphs:
                raise Exception("No text found in DOCX")
            return "\n\n".join(paragraphs)
        except Exception as e:
            raise Exception(f"Failed to read DOCX: {e}")
    
    else:
        raise Exception(f"Unsupported file type: {file_path.suffix}")
