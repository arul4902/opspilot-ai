import os
import shutil
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import User, UserRole, Document, DocumentChunk
from backend.app.rag.service import RAGService

router = APIRouter()


class DocumentChunkResponse(BaseModel):
    id: int
    chunk_index: int
    content: str
    metadata_json: str
    chroma_id: Optional[str] = None


class DocumentResponse(BaseModel):
    id: int
    filename: str
    document_type: str
    file_size: int
    chunk_count: int
    checksum: Optional[str] = None
    created_at: str


class DocumentDetailResponse(DocumentResponse):
    chunks: List[DocumentChunkResponse] = []


class CitationResponse(BaseModel):
    source_document: str
    section: str
    snippet: str
    page_number: int
    relevance_score: float
    document_id: Optional[str] = None


class KnowledgeSearchResponse(BaseModel):
    query: str
    total_results: int
    citations: List[CitationResponse]


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("operational_policy"),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Upload and index a PDF or TXT operational document into ChromaDB and SQLite.
    Restricted to Operations Agent and Admin roles.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".txt", ".md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: .pdf, .txt, .md"
        )

    upload_dir = os.path.abspath("./uploads/policies")
    os.makedirs(upload_dir, exist_ok=True)
    temp_path = os.path.join(upload_dir, file.filename)

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    rag_service = RAGService(db)
    try:
        doc = rag_service.ingest_document(temp_path, category=category)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ingestion failed: {e}")

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        document_type=doc.document_type,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        checksum=doc.checksum,
        created_at=doc.created_at.isoformat()
    )


@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all knowledge base policy documents.
    """
    rag_service = RAGService(db)
    docs = rag_service.list_documents()
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            document_type=d.document_type,
            file_size=d.file_size,
            chunk_count=d.chunk_count,
            checksum=d.checksum,
            created_at=d.created_at.isoformat()
        )
        for d in docs
    ]


@router.get("/documents/{id}", response_model=DocumentDetailResponse)
def get_document_detail(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inspect a single document and review its vectorized text chunks.
    """
    rag_service = RAGService(db)
    doc = rag_service.get_document(id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document ID {id} not found.")

    chunks = [
        DocumentChunkResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            content=c.content,
            metadata_json=c.metadata_json,
            chroma_id=c.chroma_id
        )
        for c in doc.chunks
    ]

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        document_type=doc.document_type,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        checksum=doc.checksum,
        created_at=doc.created_at.isoformat(),
        chunks=chunks
    )


@router.delete("/documents/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Delete document and purge vector embeddings from ChromaDB (Admin & Operations Agent).
    """
    rag_service = RAGService(db)
    success = rag_service.delete_document(id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document ID {id} not found.")
    return None


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_knowledge_base(
    query: str = Query(..., min_length=2, description="Search query"),
    top_k: int = Query(3, ge=1, le=10),
    min_score: float = Query(0.15, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query knowledge base using semantic vector search and return source-grounded citations.
    """
    rag_service = RAGService(db)
    results = rag_service.search(query=query, top_k=top_k, min_score=min_score)

    citations = [
        CitationResponse(
            source_document=r["source_document"],
            section=r["section"],
            snippet=r["snippet"],
            page_number=r["page_number"],
            relevance_score=r["relevance_score"],
            document_id=r.get("document_id")
        )
        for r in results
    ]

    return KnowledgeSearchResponse(
        query=query,
        total_results=len(citations),
        citations=citations
    )


@router.post("/reindex-defaults", response_model=List[DocumentResponse])
def reindex_default_policies(
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Batch ingest and reindex all 5 sample policies (PDF and TXT) into ChromaDB.
    """
    rag_service = RAGService(db)
    docs = rag_service.ingest_sample_policies()
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            document_type=d.document_type,
            file_size=d.file_size,
            chunk_count=d.chunk_count,
            checksum=d.checksum,
            created_at=d.created_at.isoformat()
        )
        for d in docs
    ]

