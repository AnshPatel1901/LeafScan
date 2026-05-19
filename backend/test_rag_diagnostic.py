"""
Diagnostic script to test RAG retrieval and identify issues.

Run with: python test_rag_diagnostic.py
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.rag_service import get_rag_service

def test_rag_health():
    print("\n" + "="*80)
    print("RAG DIAGNOSTIC TEST")
    print("="*80)
    
    rag = get_rag_service()
    
    # 1. Check if initialized
    print("\n[1] Checking RAG Service Initialization...")
    print(f"    Initialized: {rag._initialized}")
    print(f"    Documents Index Size: {len(rag._documents_index)}")
    print(f"    Indexed Documents: {list(rag._documents_index.keys())}")
    
    # 2. Get health status
    print("\n[2] RAG Service Health...")
    health = rag.health()
    for key, value in health.items():
        print(f"    {key}: {value}")
    
    # 3. List indexed documents
    print("\n[3] Indexed Documents...")
    docs = rag.list_documents()
    for doc in docs:
        print(f"    - {doc['name']}: {doc['pages']} pages, {doc['chunks']} chunks")
    
    # 4. Test search with different queries
    print("\n[4] Testing Search Queries...")
    test_queries = [
        "FUNGI",
        "RLB",
        "disease",
        "plant pathogen",
        "fungal infection",
        "what is fungi",
    ]
    
    for query in test_queries:
        print(f"\n    Query: '{query}'")
        try:
            results = rag.search(query, k=3, fetch_k=6)
            print(f"    → Found {len(results)} results")
            if results:
                for i, doc in enumerate(results, 1):
                    preview = doc.page_content[:100].replace('\n', ' ')
                    print(f"      {i}. [{doc.metadata.get('source')}] {preview}...")
            else:
                print(f"      ⚠️  NO RESULTS FOUND")
        except Exception as e:
            print(f"      ❌ ERROR: {e}")
    
    # 5. Check ChromaDB collection directly
    print("\n[5] Checking ChromaDB Collection...")
    try:
        rag._ensure_initialized()
        collection = rag._vectorstore._collection
        print(f"    Collection Name: {collection.name}")
        print(f"    Collection Count: {collection.count()}")
        
        # Try a direct collection search
        if collection.count() > 0:
            query_embedding = rag._embeddings.embed_query("FUNGI disease")
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=3,
            )
            print(f"    Direct Query Results: {len(results['ids'][0])} documents")
        else:
            print(f"    ⚠️  COLLECTION IS EMPTY!")
    except Exception as e:
        print(f"    ❌ ERROR: {e}")
    
    # 6. Check vector database directory
    print("\n[6] Vector Database Directory...")
    vec_dir = Path(rag._vector_db_dir)
    print(f"    Path: {vec_dir}")
    print(f"    Exists: {vec_dir.exists()}")
    if vec_dir.exists():
        for item in vec_dir.iterdir():
            print(f"    - {item.name}")
    
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_rag_health()
