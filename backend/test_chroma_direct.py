"""
Check ChromaDB state directly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Test ChromaDB directly
def test_chroma_direct():
    import chromadb
    
    persist_dir = "uploads/rag/vectordb"
    print(f"\nChecking ChromaDB at: {persist_dir}")
    
    # Load the client
    client = chromadb.PersistentClient(path=persist_dir)
    
    # List all collections
    collections = client.list_collections()
    print(f"\nAvailable collections: {len(collections)}")
    for col in collections:
        print(f"  - {col.name}: {col.count()} documents")
    
    # Try to load the leafscan collection
    try:
        col = client.get_collection(name="leafscan_kb_local")
        print(f"\nCollection 'leafscan_kb_local' found with {col.count()} documents")
        
        # Get some sample data
        if col.count() > 0:
            samples = col.get(limit=2)
            print(f"\nSample documents:")
            for doc_id, meta in zip(samples['ids'][:1], samples['metadatas'][:1]):
                print(f"  ID: {doc_id}")
                print(f"  Metadata: {meta}")
    except Exception as e:
        print(f"\nError loading 'leafscan_kb_local': {e}")

if __name__ == "__main__":
    test_chroma_direct()
