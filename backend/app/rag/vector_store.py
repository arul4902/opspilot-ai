import os
from typing import List, Dict, Any, Optional
import chromadb
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.rag.embeddings import OpsPilotEmbeddingFunction
from backend.app.rag.document_loader import TextChunk


class ChromaVectorStore:
    COLLECTION_NAME = "opspilot_policies"

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        os.makedirs(self.persist_directory, exist_ok=True)
        self.embedding_fn = OpsPilotEmbeddingFunction()

        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: List[TextChunk], document_id: int) -> int:
        if not chunks:
            return 0

        ids = [f"doc_{document_id}_chunk_{c.chunk_index}" for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = []
        for c in chunks:
            meta = dict(c.metadata)
            meta["document_id"] = str(document_id)
            # Ensure all values are primitives (str, int, float, bool)
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            metadatas.append(clean_meta)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Indexed {len(chunks)} chunks into ChromaDB for Document ID {document_id}")
        return len(chunks)

    def query(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        count = self.collection.count()
        if count == 0:
            return []

        actual_k = min(n_results, count)
        results = self.collection.query(
            query_texts=[query_text],
            n_results=actual_k
        )

        matched: List[Dict[str, Any]] = []
        if not results or not results.get("documents") or not results["documents"][0]:
            return matched

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            # For cosine distance: cosine similarity = 1 - distance
            similarity = max(0.0, min(1.0, 1.0 - dist))
            matched.append({
                "content": doc,
                "metadata": meta,
                "document_name": meta.get("document_name", "Policy Manual"),
                "section": meta.get("section", "Standard Guidelines"),
                "page_number": meta.get("page_number", 1),
                "category": meta.get("category", "policy"),
                "document_id": meta.get("document_id"),
                "relevance_score": round(similarity, 4)
            })

        return matched

    def delete_by_document_id(self, document_id: int) -> int:
        try:
            # Query chunks belonging to document
            res = self.collection.get(where={"document_id": str(document_id)})
            ids_to_del = res.get("ids", [])
            if ids_to_del:
                self.collection.delete(ids=ids_to_del)
                logger.info(f"Deleted {len(ids_to_del)} chunks from ChromaDB for Document ID {document_id}")
                return len(ids_to_del)
            return 0
        except Exception as e:
            logger.error(f"Failed to delete chunks for document {document_id}: {e}")
            return 0

    def count(self) -> int:
        return self.collection.count()

    def reset(self):
        try:
            self.client.delete_collection(self.COLLECTION_NAME)
            self.collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.warning(f"Chroma reset warning: {e}")
