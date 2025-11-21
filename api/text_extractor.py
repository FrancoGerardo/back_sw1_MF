import os
from pypdf import PdfReader
from docx import Document
import io

def _extract_text_from_txt(file_path):
    """Extrae texto de un archivo .txt simple."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error leyendo TXT: {e}")
        return ""

def _extract_text_from_pdf(file_path):
    """Extrae texto de un archivo .pdf."""
    try:
        reader = PdfReader(file_path)
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or "")
        return "\n".join(text)
    except Exception as e:
        print(f"Error leyendo PDF: {e}")
        return ""

def _extract_text_from_docx(file_path):
    """Extrae texto de un archivo .docx."""
    try:
        doc = Document(file_path)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        return "\n".join(text)
    except Exception as e:
        print(f"Error leyendo DOCX: {e}")
        return ""

def extract_text(document):
    """
    Función principal que recibe un objeto Documento de Django,
    revisa su extensión y llama al extractor correspondiente.
    """
    try:
        file_path = document.file.path
        # Obtener la extensión del archivo
        _, extension = os.path.splitext(file_path)
        extension = extension.lower()

        if extension == '.txt':
            return _extract_text_from_txt(file_path)
        
        elif extension == '.pdf':
            return _extract_text_from_pdf(file_path)
        
        elif extension == '.docx':
            return _extract_text_from_docx(file_path)
        
        else:
            # Tipo de archivo no soportado
            return ""
            
    except Exception as e:
        print(f"Error general al extraer texto del documento {document.id}: {e}")
        return ""