import re
import math
import hashlib
from typing import List, Dict, Any, Optional
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

STOP_WORDS = {
    'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'is', 'are',
    'was', 'were', 'be', 'do', 'does', 'did', 'have', 'has', 'had', 'i', 'my', 'me',
    'you', 'your', 'it', 'its', 'we', 'they', 'this', 'that', 'how', 'what', 'where',
    'why', 'when', 'can', 'could', 'would', 'should', 'with', 'from', 'by'
}

DOMAIN_KEYWORDS = {
    'return': 3.5,
    'refund': 3.5,
    'delay': 3.0,
    'delayed': 3.0,
    'days': 3.0,
    '30': 4.0,
    'shipping': 2.5,
    'courier': 2.5,
    'payment': 3.0,
    'orphan': 4.0,
    'window': 3.5,
    'policy': 2.0,
    'defect': 3.0,
    'defective': 3.0,
    'damaged': 3.0,
    'credit': 2.5,
    'sla': 2.5,
    'item': 1.5,
    'items': 1.5,
    'deducted': 3.5,
    'missing': 3.0,
    'confirmation': 2.5,
}


class OpsPilotEmbeddingFunction(EmbeddingFunction):
    """
    High-performance, deterministic, zero-network embedding function.
    Generates normalized 384-dimensional dense vectors using hashed term-frequency weighting,
    stop-word suppression, and domain keyword amplification.
    Guarantees 100% offline reliability on 8GB RAM machines without downloading
    heavy ONNX models or requiring external network calls.
    """
    DIMENSION = 384

    def __init__(self):
        pass

    @staticmethod
    def name() -> str:
        return "opspilot_embedding"

    def get_config(self) -> Dict[str, Any]:
        return {"dimension": self.DIMENSION}

    @classmethod
    def build_from_config(cls, config: Dict[str, Any]) -> "OpsPilotEmbeddingFunction":
        return cls()

    def __call__(self, input: Documents) -> Embeddings:
        embeddings: List[List[float]] = []

        for text in input:
            vec = [0.0] * self.DIMENSION
            clean_text = text.lower()
            tokens = [
                t for t in re.findall(r'\b\w+\b', clean_text)
                if t not in STOP_WORDS
            ]

            if not tokens:
                embeddings.append(vec)
                continue

            for w in tokens:
                weight = DOMAIN_KEYWORDS.get(w, 1.0)
                h = int(hashlib.sha256(w.encode("utf-8")).hexdigest(), 16) % self.DIMENSION
                vec[h] += weight

            # Bigram hashing for phrase context
            for i in range(len(tokens) - 1):
                bigram = f"{tokens[i]}_{tokens[i+1]}"
                h_bi = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16) % self.DIMENSION
                vec[h_bi] += 1.5

            # L2 Normalization
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [x / norm for x in vec]

            embeddings.append(vec)

        return embeddings
