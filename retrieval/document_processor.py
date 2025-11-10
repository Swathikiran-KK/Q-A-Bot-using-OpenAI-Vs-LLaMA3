from PyPDF2 import PdfReader
from docx import Document
import pandas as pd
from io import BytesIO
from typing import List, Dict

def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    text = ""
    for p in reader.pages:
        text += p.extract_text() or ""
    return text

def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_from_csv(file_bytes: bytes, max_rows: int = 1000) -> str:
    df = pd.read_csv(BytesIO(file_bytes))
    if len(df) > max_rows:
        df = df.head(max_rows)
    return df.to_csv(index=False)

def chunk_text(text: str, chunk_size=900, overlap=120) -> List[Dict]:
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        chunks.append({"text": chunk, "metadata": {"start": start, "end": end}})
        start += max(1, chunk_size - overlap)
    return chunks
