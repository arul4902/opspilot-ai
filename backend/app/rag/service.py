import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.core.logging import logger
from backend.app.models.models import Document, DocumentChunk
from backend.app.rag.document_loader import DocumentLoader, TextChunk
from backend.app.rag.vector_store import ChromaVectorStore


class RAGCitation(BaseModel if False else object):
    def __init__(self, source_document: str, section: str, snippet: str, relevance_score: float, page_number: int = 1):
        self.source_document = source_document
        self.section = section
        self.snippet = snippet
        self.relevance_score = relevance_score
        self.page_number = page_number

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_document": self.source_document,
            "section": self.section,
            "snippet": self.snippet,
            "relevance_score": self.relevance_score,
            "page_number": self.page_number
        }


class RAGService:
    def __init__(self, db: Session, persist_dir: Optional[str] = None):
        self.db = db
        self.loader = DocumentLoader(chunk_size=500, chunk_overlap=80)
        self.vector_store = ChromaVectorStore(persist_directory=persist_dir)

    def calculate_checksum(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def ingest_document(
        self,
        file_path: str,
        category: str = "policy",
        document_type: str = "policy"
    ) -> Document:
        """
        Ingest a file (PDF or TXT) into SQL database and ChromaDB vector store.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        checksum = self.calculate_checksum(file_path)

        # Check if already ingested with same checksum
        existing = self.db.query(Document).filter(Document.checksum == checksum).first()
        if existing:
            try:
                chroma_res = self.vector_store.collection.get(where={"document_id": str(existing.id)})
                if not chroma_res or not chroma_res.get("ids"):
                    chunks = self.loader.load_and_chunk(file_path, category=category)
                    self.vector_store.add_chunks(chunks=chunks, document_id=existing.id)
            except Exception as e:
                logger.warning(f"Chroma sync check for doc {existing.id}: {e}")
            logger.info(f"Document '{filename}' already ingested (ID {existing.id}, checksum match).")
            return existing

        # Load and chunk text
        chunks: List[TextChunk] = self.loader.load_and_chunk(file_path, category=category)
        if not chunks:
            raise ValueError(f"No extractable text found in '{filename}'.")

        # Create Document record
        doc = Document(
            filename=filename,
            file_path=file_path,
            document_type=document_type,
            file_size=file_size,
            chunk_count=len(chunks),
            checksum=checksum
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        # Create DocumentChunk records
        db_chunks = []
        for c in chunks:
            chroma_id = f"doc_{doc.id}_chunk_{c.chunk_index}"
            chunk_row = DocumentChunk(
                document_id=doc.id,
                chunk_index=c.chunk_index,
                content=c.content,
                metadata_json=json.dumps(c.metadata),
                chroma_id=chroma_id
            )
            db_chunks.append(chunk_row)

        self.db.add_all(db_chunks)
        self.db.commit()

        # Index in ChromaDB
        self.vector_store.add_chunks(chunks=chunks, document_id=doc.id)
        logger.info(f"Successfully ingested '{filename}' with {len(chunks)} chunks.")
        return doc

    def search(self, query: str, top_k: int = 3, min_score: float = 0.20) -> List[Dict[str, Any]]:
        """
        Retrieve relevant policy chunks using vector similarity search.
        """
        raw_results = self.vector_store.query(query_text=query, n_results=top_k)

        citations = []
        for r in raw_results:
            if r["relevance_score"] >= min_score:
                citations.append({
                    "source_document": r["document_name"],
                    "section": r["section"],
                    "snippet": r["content"],
                    "page_number": r["page_number"],
                    "relevance_score": r["relevance_score"],
                    "document_id": r.get("document_id")
                })

        return citations

    def delete_document(self, document_id: int) -> bool:
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return False

        # Remove from ChromaDB
        self.vector_store.delete_by_document_id(document_id)

        # Remove from SQL (cascades to chunks)
        self.db.delete(doc)
        self.db.commit()
        logger.info(f"Document ID {document_id} and all related chunks deleted.")
        return True

    def list_documents(self) -> List[Document]:
        return self.db.query(Document).order_by(Document.created_at.desc()).all()

    def get_document(self, document_id: int) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def ingest_sample_policies(self, sample_dir: Optional[str] = None) -> List[Document]:
        if not sample_dir:
            sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "sample-data", "policies"))

        if not os.path.exists(sample_dir):
            logger.warning(f"Sample policies directory not found: {sample_dir}")
            return []

        ingested = []
        for fname in os.listdir(sample_dir):
            if fname.endswith(".txt") or fname.endswith(".pdf"):
                full_path = os.path.join(sample_dir, fname)
                try:
                    doc = self.ingest_document(full_path, category="operational_policy")
                    ingested.append(doc)
                except Exception as e:
                    logger.error(f"Failed to ingest policy '{fname}': {e}")

        return ingested

