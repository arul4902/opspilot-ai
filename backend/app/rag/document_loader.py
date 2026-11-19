import os
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pypdf


class TextChunk(BaseModel):
    chunk_index: int
    content: str
    metadata: Dict[str, Any]


class DocumentLoader:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_and_chunk(self, file_path: str, category: str = "policy") -> List[TextChunk]:
        """
        Loads document from file path (PDF or TXT) and decomposes it into overlapping chunks.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")

        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            pages = self._extract_pdf_pages(file_path)
        elif ext in [".txt", ".md", ".json", ".csv"]:
            pages = self._extract_txt_pages(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Only PDF and TXT are supported.")

        chunks: List[TextChunk] = []
        global_index = 0

        for page_num, text in pages:
            page_chunks = self._split_text_into_chunks(
                text=text,
                page_number=page_num,
                filename=filename,
                category=category,
                start_index=global_index
            )
            chunks.extend(page_chunks)
            global_index += len(page_chunks)

        return chunks

    def _extract_pdf_pages(self, file_path: str) -> List[tuple[int, str]]:
        pages = []
        try:
            reader = pypdf.PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                extracted = page.extract_text() or ""
                clean_text = self._clean_text(extracted)
                if clean_text:
                    pages.append((idx + 1, clean_text))
        except Exception as e:
            raise RuntimeError(f"Failed to read PDF file '{file_path}': {e}")
        return pages

    def _extract_txt_pages(self, file_path: str) -> List[tuple[int, str]]:
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        content = ""
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        clean_text = self._clean_text(content)
        return [(1, clean_text)] if clean_text else []

    def _clean_text(self, text: str) -> str:
        # Normalize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Remove decorative horizontal separator rules
        text = re.sub(r'[=\-]{5,}', '', text)
        # Remove consecutive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove null characters
        text = text.replace("\x00", "")
        return text.strip()

    def _detect_section(self, text: str) -> str:
        # Detect patterns like: "1. GENERAL RETURN WINDOW", "Section 2.1", "POLICY: ..."
        match = re.search(r'(?:Section\s+\d+(?:\.\d+)?|\b\d+\.\s+[A-Z\s]{4,}|POLICY:\s+[A-Z\s]+)', text)
        if match:
            return match.group(0).strip()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return lines[0][:60] if lines else "General Operational Guidance"

    def _split_text_into_chunks(
        self,
        text: str,
        page_number: int,
        filename: str,
        category: str,
        start_index: int
    ) -> List[TextChunk]:
        chunks: List[TextChunk] = []
        if not text:
            return chunks

        # Try to split by paragraphs first
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current_chunk = ""
        current_section = self._detect_section(text)
        index = start_index

        for para in paragraphs:
            # Check if paragraph has its own section header
            sec_match = self._detect_section(para)
            if sec_match and sec_match != "General Operational Guidance":
                current_section = sec_match

            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(
                        TextChunk(
                            chunk_index=index,
                            content=current_chunk,
                            metadata={
                                "filename": filename,
                                "document_name": filename,
                                "page_number": page_number,
                                "category": category,
                                "section": current_section,
                                "chunk_index": index
                            }
                        )
                    )
                    index += 1

                # If single paragraph is longer than chunk_size, split by sliding window
                if len(para) > self.chunk_size:
                    step = self.chunk_size - self.chunk_overlap
                    for start in range(0, len(para), step):
                        sub_text = para[start:start + self.chunk_size].strip()
                        if sub_text:
                            chunks.append(
                                TextChunk(
                                    chunk_index=index,
                                    content=sub_text,
                                    metadata={
                                        "filename": filename,
                                        "document_name": filename,
                                        "page_number": page_number,
                                        "category": category,
                                        "section": current_section,
                                        "chunk_index": index
                                    }
                                )
                            )
                            index += 1
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(
                TextChunk(
                    chunk_index=index,
                    content=current_chunk,
                    metadata={
                        "filename": filename,
                        "document_name": filename,
                        "page_number": page_number,
                        "category": category,
                        "section": current_section,
                        "chunk_index": index
                    }
                )
            )

        return chunks

