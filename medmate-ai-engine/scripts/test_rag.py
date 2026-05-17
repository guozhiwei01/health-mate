"""
RAG Pipeline Test
1. Initialize KnowledgeManager (BGE-M3 + Milvus + ES)
2. Ingest medical knowledge
3. Test hybrid retrieval
4. Test reranking
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
os.environ["USE_TF"] = "0"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("HealthMate RAG Pipeline Test")
print("=" * 60)

# Step 1: Initialize
print("\n[Step 1] Initializing KnowledgeManager...")
from app.rag.knowledge_manager import knowledge_manager
knowledge_manager.init()

# Step 2: Ingest knowledge
print("\n[Step 2] Ingesting medical knowledge...")
knowledge_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")
total = knowledge_manager.ingest_directory(knowledge_dir, category="medical_guidelines")
print(f"Total chunks indexed: {total}")

stats = knowledge_manager.get_stats()
print(f"Stats: {stats}")

# Step 3: Test hybrid retrieval
print("\n[Step 3] Testing hybrid retrieval...")
from app.rag.retriever import hybrid_retriever

queries = [
    "headache for two days with nausea",
    "can ibuprofen be taken with amoxicillin",
    "what is normal blood pressure",
    "chest pain emergency",
]

for query in queries:
    results = hybrid_retriever.search(query, top_k=3)
    print(f"\nQuery: '{query}'")
    for i, r in enumerate(results):
        print(f"  [{i+1}] score={r.score:.4f} src={r.source} | {r.content[:80]}...")

# Step 4: Test reranking
print("\n[Step 4] Testing reranking...")
from app.rag.reranker import bge_reranker

query = "headache treatment options"
raw_results = hybrid_retriever.search(query, top_k=10)
reranked = bge_reranker.rerank(query, raw_results)

print(f"\nQuery: '{query}'")
print(f"Before rerank: {len(raw_results)} results")
print(f"After rerank: {len(reranked)} results (top 5)")
for i, r in enumerate(reranked):
    print(f"  [{i+1}] score={r.score:.4f} | {r.content[:80]}...")

print("\n" + "=" * 60)
print("RAG Pipeline Test COMPLETE")
print("=" * 60)
