"""
OpsPilot AI - Knowledge Base Ingestion CLI Script
Ingests all operational policies (PDF and TXT) from sample-data/policies into SQLite & ChromaDB.
"""
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal
from backend.app.rag.service import RAGService


def main():
    print("==================================================")
    print(" OpsPilot AI: Knowledge Base Ingestion CLI")
    print("==================================================")

    db = SessionLocal()
    try:
        rag_service = RAGService(db)
        print("Starting batch ingestion from 'sample-data/policies/'...")
        docs = rag_service.ingest_sample_policies()
        print(f"\nSuccessfully ingested {len(docs)} policy documents:")
        for d in docs:
            print(f" - [{d.document_type.upper()}] {d.filename} ({d.chunk_count} chunks, {d.file_size} bytes)")

        total_chunks = rag_service.vector_store.count()
        print(f"\nTotal vectors indexed in ChromaDB: {total_chunks}")
        print("RAG Knowledge Base is ready for autonomous agent retrieval.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

