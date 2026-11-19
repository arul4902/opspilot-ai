import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.rag.document_loader import DocumentLoader
from backend.app.rag.embeddings import OpsPilotEmbeddingFunction
from backend.app.rag.vector_store import ChromaVectorStore
from backend.app.rag.service import RAGService
from backend.app.models.models import Document, DocumentChunk


def test_document_loader_txt():
    loader = DocumentLoader(chunk_size=300, chunk_overlap=50)
    sample_txt = os.path.abspath("sample-data/policies/return_policy.txt")
    chunks = loader.load_and_chunk(sample_txt, category="policy")

    assert len(chunks) > 0
    assert "return" in chunks[0].content.lower()
    assert chunks[0].metadata["filename"] == "return_policy.txt"
    assert chunks[0].metadata["category"] == "policy"


def test_document_loader_pdf():
    loader = DocumentLoader(chunk_size=400, chunk_overlap=60)
    sample_pdf = os.path.abspath("sample-data/policies/shipping_sla_policy.pdf")
    chunks = loader.load_and_chunk(sample_pdf, category="sla")

    assert len(chunks) > 0
    assert chunks[0].metadata["filename"] == "shipping_sla_policy.pdf"
    assert chunks[0].metadata["page_number"] >= 1


def test_embedding_function():
    embedder = OpsPilotEmbeddingFunction()
    docs = ["Customer return window is 30 days.", "Courier delay due to severe weather."]
    vectors = embedder(docs)

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    # Test L2 normalization
    norm = sum(x * x for x in vectors[0]) ** 0.5
    assert abs(norm - 1.0) < 1e-4


def test_vector_store_lifecycle(tmp_path):
    test_dir = str(tmp_path / "test_chroma")
    vstore = ChromaVectorStore(persist_directory=test_dir)

    loader = DocumentLoader()
    sample_txt = os.path.abspath("sample-data/policies/return_policy.txt")
    chunks = loader.load_and_chunk(sample_txt)

    # Add chunks
    count_added = vstore.add_chunks(chunks, document_id=999)
    assert count_added == len(chunks)
    assert vstore.count() == len(chunks)

    # Query
    results = vstore.query("return policy 30 calendar days", n_results=2)
    assert len(results) > 0
    assert results[0]["relevance_score"] > 0.0

    # Delete
    deleted = vstore.delete_by_document_id(999)
    assert deleted == len(chunks)
    assert vstore.count() == 0


def test_rag_service_search(db_session: Session):
    rag_service = RAGService(db_session)
    # Ensure sample policies are indexed
    rag_service.ingest_sample_policies()

    # Search return window
    results = rag_service.search("What is the return time limit?", top_k=2)
    assert len(results) > 0
    assert any("30" in r["snippet"] or "return" in r["snippet"].lower() for r in results)

    # Search delivery delay compensation
    delay_res = rag_service.search("delivery delay courier exception compensation", top_k=2)
    assert len(delay_res) > 0
    assert any("10" in r["snippet"] or "delay" in r["snippet"].lower() for r in delay_res)


def test_knowledge_api_search_and_list(client: TestClient, auth_headers: dict):
    # List documents
    list_res = client.get("/api/v1/knowledge/documents", headers=auth_headers)
    assert list_res.status_code == 200
    docs = list_res.json()
    assert len(docs) > 0

    # Search endpoint
    search_res = client.get("/api/v1/knowledge/search?query=return+policy+days", headers=auth_headers)
    assert search_res.status_code == 200
    s_data = search_res.json()
    assert s_data["total_results"] > 0
    assert len(s_data["citations"]) > 0
    assert "source_document" in s_data["citations"][0]


def test_knowledge_api_upload_and_delete(client: TestClient, auth_headers: dict):
    # Create temporary text policy
    dummy_content = (
        "ENTERPRISE POLICY: SPECIAL HOLIDAY RETURN WINDOW\n\n"
        "During December holiday seasons, the return window is extended to 60 days.\n\n"
        "All tags must remain attached."
    )
    files = {"file": ("holiday_return_policy.txt", dummy_content.encode("utf-8"), "text/plain")}
    data = {"category": "holiday_policy"}

    upload_res = client.post("/api/v1/knowledge/upload", headers=auth_headers, files=files, data=data)
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["filename"] == "holiday_return_policy.txt"
    assert doc_data["chunk_count"] > 0

    # Get document detail
    detail_res = client.get(f"/api/v1/knowledge/documents/{doc_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    assert len(detail_res.json()["chunks"]) > 0

    # Delete document
    del_res = client.delete(f"/api/v1/knowledge/documents/{doc_id}", headers=auth_headers)
    assert del_res.status_code == 204

