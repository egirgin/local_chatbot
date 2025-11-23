import os
import pypdf
from config import PDF_FUNCTIONALITY_DISABLED

def read_image_bytes_from_file(image_path: str) -> bytes | None:
    """Reads an image file and returns its binary content (bytes)."""
    if not os.path.exists(image_path):
        print(f"ERROR: Image file not found: {image_path}")
        return None
    try:
        with open(image_path, "rb") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading image file {image_path}: {e}")
        return None

def read_text_file(file_path: str) -> str | None:
    """Reads a text-based file and returns its content."""
    try:
        # Using utf-8 with error handling
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading text file {file_path}: {e}")
        return None

def extract_pdf_text(file_path: str) -> str | None:
    """Extracts text from a PDF file."""
    if PDF_FUNCTIONALITY_DISABLED:
        print(f"Error: PDF processing is disabled (pypdf not found).")
        return None
    try:
        reader = pypdf.PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        return "\n".join(text_parts)
    except Exception as e:
        print(f"Error extracting PDF text from {file_path}: {e}")
        return None