"""
Test RAG search with embeddings to see why queries are returning no results.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_search_with_embeddings():
    from app.services.rag_service import get_rag_service
    
    rag = get_rag_service()
    
    print("\n" + "="*80)
    print("Testing RAG Search with Embeddings")
    print("="*80)
    
    # Ensure initialized
    rag._ensure_initialized()
    print(f"\nVectorstore initialized: {rag._vectorstore is not None}")
    print(f"Embeddings model: {rag._embeddings.__class__.__name__}")
    
    # Test queries
    queries = [
        "FUNGI",
        "fungal disease",
        "RLB resistant",
        "plant pathogen",
        "what is fungi",
        "disease management",
    ]
    
    for query in queries:
        print(f"\n{'─'*80}")
        print(f"Query: '{query}'")
        print(f"{'─'*80}")
        
        try:
            # Try with direct retriever
            retriever = rag._vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={"k": 3, "fetch_k": 6, "lambda_mult": 0.5},
            )
            docs = retriever.invoke(query)
            print(f"Results: {len(docs)} documents found")
            
            if docs:
                for i, doc in enumerate(docs, 1):
                    source = doc.metadata.get('source', 'Unknown')
                    page = doc.metadata.get('page', '?')
                    chunk_idx = doc.metadata.get('chunk_index', '?')
                    preview = doc.page_content[:150].replace('\n', ' ')
                    print(f"\n  [{i}] {source} (page {page}, chunk {chunk_idx})")
                    print(f"      {preview}...")
            else:
                print("  ⚠️  NO RESULTS")
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_search_with_embeddings()
