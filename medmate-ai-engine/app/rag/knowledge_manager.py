"""
RAG Knowledge Manager
- Load medical documents (text/markdown)
- Chunk with overlap
- Embed with BGE-M3 (XLMRoberta backbone)
- Store in Milvus (vector) + Elasticsearch (BM25)
"""
import os
import json
import hashlib
from typing import Optional

import torch
from transformers import AutoModel, AutoTokenizer, AutoConfig
from pymilvus import (
    connections, utility, Collection, CollectionSchema,
    FieldSchema, DataType,
)
from elasticsearch import Elasticsearch

from app.config import settings


# Milvus collection config
COLLECTION_NAME = settings.milvus_collection
VECTOR_DIM = 1024  # BGE-M3 output dimension


class KnowledgeManager:
    """Manage medical knowledge base: embed, store, retrieve"""

    def __init__(self):
        self.embed_model = None
        self.embed_tokenizer = None
        self.milvus_collection: Optional[Collection] = None
        self.es_client: Optional[Elasticsearch] = None
        self.is_ready = False

    def init(self):
        """Initialize all connections and models"""
        self._load_embedding_model()
        self._connect_milvus()
        self._connect_elasticsearch()
        self.is_ready = True
        print("[OK] KnowledgeManager initialized", flush=True)

    # ==================== Embedding ====================

    def _load_embedding_model(self):
        """Load BGE-M3 using transformers AutoModel"""
        model_path = settings.embedding_model_path
        print(f"[LOAD] Loading BGE-M3 from {model_path}...", flush=True)

        # Load config and force model_type for compatibility
        config = AutoConfig.from_pretrained(model_path, model_type="xlm-roberta")
        self.embed_tokenizer = AutoTokenizer.from_pretrained(model_path, config=config)
        self.embed_model = AutoModel.from_pretrained(model_path, config=config)
        self.embed_model.eval()
        if torch.cuda.is_available():
            self.embed_model = self.embed_model.cuda()
        print(f"[OK] BGE-M3 loaded (dim={VECTOR_DIM})", flush=True)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using BGE-M3 with [CLS] pooling + L2 normalize"""
        device = next(self.embed_model.parameters()).device
        encoded = self.embed_tokenizer(
            texts, padding=True, truncation=True,
            max_length=512, return_tensors="pt"
        ).to(device)

        with torch.no_grad():
            outputs = self.embed_model(**encoded)
            # [CLS] token embedding
            embeddings = outputs.last_hidden_state[:, 0, :]
            # L2 normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().float().tolist()

    # ==================== Milvus ====================

    def _connect_milvus(self):
        """Connect to Milvus and ensure collection exists"""
        print("[CONN] Connecting to Milvus...", flush=True)
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=settings.milvus_port,
        )

        if not utility.has_collection(COLLECTION_NAME):
            self._create_milvus_collection()
        else:
            self.milvus_collection = Collection(COLLECTION_NAME)
            self.milvus_collection.load()
        print(f"[OK] Milvus collection '{COLLECTION_NAME}' ready", flush=True)

    def _create_milvus_collection(self):
        """Create Milvus collection with schema"""
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
        ]
        schema = CollectionSchema(fields, description="Medical knowledge base")
        self.milvus_collection = Collection(COLLECTION_NAME, schema)

        # Create HNSW index
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 256},
        }
        self.milvus_collection.create_index("vector", index_params)
        self.milvus_collection.load()
        print(f"[OK] Created Milvus collection '{COLLECTION_NAME}' with HNSW index", flush=True)

    # ==================== Elasticsearch ====================

    def _connect_elasticsearch(self):
        """Connect to Elasticsearch and ensure index exists"""
        print("[CONN] Connecting to Elasticsearch...", flush=True)
        self.es_client = Elasticsearch(settings.es_url)

        try:
            info = self.es_client.info()
            print(f"  ES version: {info['version']['number']}", flush=True)
        except Exception as e:
            print(f"[WARN] ES connection issue: {e}", flush=True)

        try:
            if not self.es_client.indices.exists(index=settings.es_index).body:
                self._create_es_index()
        except Exception:
            # Index doesn't exist or check failed, try creating
            try:
                self._create_es_index()
            except Exception:
                pass  # Already exists
        print(f"[OK] Elasticsearch index '{settings.es_index}' ready", flush=True)

    def _create_es_index(self):
        """Create ES index for Chinese text search"""
        self.es_client.indices.create(
            index=settings.es_index,
            mappings={
                "properties": {
                    "id":       {"type": "keyword"},
                    "content":  {"type": "text", "analyzer": "standard"},
                    "source":   {"type": "keyword"},
                    "category": {"type": "keyword"},
                }
            }
        )

    # ==================== Ingest ====================

    def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 128) -> list[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start += chunk_size - overlap
        return chunks

    def ingest_document(self, content: str, source: str, category: str = "general"):
        """Ingest a document: chunk -> embed -> store in Milvus + ES"""
        chunks = self.chunk_text(content)
        if not chunks:
            return 0

        # Generate IDs
        ids = []
        for i, chunk in enumerate(chunks):
            doc_hash = hashlib.md5(f"{source}_{i}_{chunk[:50]}".encode()).hexdigest()[:16]
            ids.append(doc_hash)

        # Embed
        vectors = self.embed(chunks)

        # Insert into Milvus
        self.milvus_collection.insert([
            ids,                                    # id
            chunks,                                 # content
            [source] * len(chunks),                 # source
            [category] * len(chunks),               # category
            vectors,                                # vector
        ])
        self.milvus_collection.flush()

        # Insert into Elasticsearch
        for doc_id, chunk in zip(ids, chunks):
            self.es_client.index(
                index=settings.es_index,
                id=doc_id,
                document={
                    "id": doc_id,
                    "content": chunk,
                    "source": source,
                    "category": category,
                }
            )

        print(f"[INGEST] {source}: {len(chunks)} chunks indexed", flush=True)
        return len(chunks)

    def ingest_directory(self, dir_path: str, category: str = "general") -> int:
        """Ingest all .txt/.md files from a directory"""
        total = 0
        for filename in os.listdir(dir_path):
            if filename.endswith((".txt", ".md")):
                filepath = os.path.join(dir_path, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                total += self.ingest_document(content, source=filename, category=category)
        return total

    def get_stats(self) -> dict:
        """Get knowledge base statistics"""
        milvus_count = self.milvus_collection.num_entities if self.milvus_collection else 0
        es_count = 0
        if self.es_client:
            try:
                es_count = self.es_client.count(index=settings.es_index)["count"]
            except Exception:
                pass
        return {"milvus_chunks": milvus_count, "es_chunks": es_count}


# Singleton
knowledge_manager = KnowledgeManager()
