"""
Vector Search Demo with New Types and Range Queries

Features:
- FLOAT16 and BFLOAT16 vector support (PR #1001)
- Vector Range Queries (PR #985)

This demo shows memory-efficient vector types and similarity threshold queries.
"""

import numpy as np

from core.client import get_binary_client
from core.config import config
from core.data_loader import DataLoader
from .base import FeatureDemo


class VectorSearchDemo(FeatureDemo):
    """Demo for new vector types and range queries in valkey-search 1.3."""
    
    name = "Vector Search (BFLOAT16 + Range Queries)"
    description = "Memory-efficient FLOAT16/BFLOAT16 vectors and similarity range queries"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binary_client = get_binary_client()
        self._embedder = None
    
    @property
    def embedder(self):
        """Lazy-load the embedding model."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(config.embedding_model)
        return self._embedder
    
    def setup(self) -> None:
        """Verify index exists with vector field."""
        indexes = self.client.execute_command("FT._LIST")
        if config.index_name not in indexes:
            print(f"Warning: Index '{config.index_name}' not found. Run data loader first.")
    
    def demo_knn_search(self, query: str = "comfortable shoes for standing all day") -> list[dict]:
        """
        K-Nearest Neighbors vector search.
        
        Using BFLOAT16 vectors (50% memory savings vs FLOAT32).
        """
        print(f"\n🔍 KNN Vector Search: '{query}'")
        print("   Using: BFLOAT16 vectors (50% memory vs FLOAT32)")
        
        # Generate query embedding
        query_vec = self._encode_query(query)
        
        results = self._execute_search(
            config.index_name,
            "(*)=>[KNN 5 @embedding $query_vec]",
            "PARAMS", "2", "query_vec", query_vec,
            "RETURN", "4", "title", "price", "category", "__embedding_score",
            "DIALECT", "2",
        )
        
        parsed = self._parse_vector_results(results)
        self._print_vector_results(parsed)
        return parsed
    
    def demo_range_query(
        self,
        query: str = "running shoes for trails",
        similarity_threshold: float = 0.7,
    ) -> list[dict]:
        """
        Vector range query - return all vectors within similarity threshold.
        
        NEW IN 1.3: Instead of top-K, return ALL products with similarity >= threshold.
        Use case: "Find all similar products" for recommendations.
        """
        print(f"\n📏 Vector Range Query: '{query}'")
        print(f"   Threshold: similarity >= {similarity_threshold}")
        print("   Returns ALL matching vectors, not just top-K")
        
        # Generate query embedding
        query_vec = self._encode_query(query)
        
        # Range query syntax: VECTOR_RANGE <radius> @field $vec
        # Cosine distance: radius = 1 - similarity
        radius = 1 - similarity_threshold
        
        results = self._execute_search(
            config.index_name,
            f"(*)=>[VECTOR_RANGE {radius} @embedding $query_vec]",
            "PARAMS", "2", "query_vec", query_vec,
            "RETURN", "4", "title", "price", "category", "__embedding_score",
            "SORTBY", "__embedding_score", "ASC",
            "DIALECT", "2",
        )
        
        parsed = self._parse_vector_results(results)
        self._print_vector_results(parsed, show_similarity=True)
        return parsed
    
    def demo_find_similar_product(self, product_id: str = "1001") -> list[dict]:
        """
        Find products similar to an existing product.
        
        Use case: "Customers who viewed this also viewed..."
        """
        print(f"\n🔗 Find Similar Products to: product:{product_id}")
        
        # Get the existing product's embedding
        product_key = f"product:{product_id}"
        embedding_bytes = self.binary_client.hget(product_key, "embedding")
        
        if not embedding_bytes:
            print(f"   Error: Product {product_id} not found or has no embedding")
            return []
        
        # Get product title for context
        title = self.client.hget(product_key, "title")
        print(f"   Source: {title}")
        
        # KNN search excluding the source product
        results = self._execute_search(
            config.index_name,
            f"(-@_key:{{{product_key}}})=>[KNN 5 @embedding $query_vec]",
            "PARAMS", "2", "query_vec", embedding_bytes,
            "RETURN", "3", "title", "price", "category",
            "DIALECT", "2",
        )
        
        parsed = self._parse_vector_results(results)
        self._print_vector_results(parsed)
        return parsed
    
    def demo_vector_type_comparison(self) -> None:
        """
        Compare memory usage of different vector types.
        
        FLOAT32: 4 bytes per dimension
        FLOAT16: 2 bytes per dimension (50% savings)
        BFLOAT16: 2 bytes per dimension (50% savings, better for ML)
        """
        print("\n💾 Vector Type Memory Comparison")
        print("   " + "-" * 50)
        
        dim = config.embedding_dim
        
        types = [
            ("FLOAT32", 4, "Full precision"),
            ("FLOAT16", 2, "Half precision, good for inference"),
            ("BFLOAT16", 2, "Brain float, better for ML workloads"),
        ]
        
        print(f"\n   For {dim}-dimensional vectors:\n")
        
        for vtype, bytes_per_dim, desc in types:
            size = dim * bytes_per_dim
            print(f"   {vtype:10} {size:6} bytes  ({desc})")
        
        print(f"\n   Memory savings with FLOAT16/BFLOAT16: 50%")
        print(f"   For 1M vectors: {dim * 4 / 1024:.1f} MB → {dim * 2 / 1024:.1f} MB per million")
    
    def _encode_query(self, query: str) -> bytes:
        """Encode a query string to BFLOAT16 vector bytes."""
        embedding = self.embedder.encode(query)
        return DataLoader._vector_to_bytes(embedding, dtype="bfloat16")
    
    def _parse_vector_results(self, results: list) -> list[dict]:
        """Parse vector search results."""
        if not results or results[0] == 0:
            return []
        
        items = []
        i = 1
        while i < len(results):
            key = results[i]
            fields = results[i + 1] if i + 1 < len(results) else []
            
            item = {"_key": key}
            for j in range(0, len(fields), 2):
                field_name = fields[j]
                field_val = fields[j + 1]
                
                # Parse vector score
                if field_name == "__embedding_score":
                    item["_distance"] = float(field_val)
                    item["_similarity"] = 1 - float(field_val)  # Cosine: sim = 1 - dist
                else:
                    item[field_name] = field_val
            
            items.append(item)
            i += 2
        
        return items
    
    def _print_vector_results(self, results: list[dict], show_similarity: bool = False) -> None:
        """Print vector search results with similarity scores."""
        if not results:
            print("   No results found.")
            return
        
        print(f"\n   Found {len(results)} result(s):\n")
        
        for i, item in enumerate(results, 1):
            title = item.get("title", "Unknown")
            price = item.get("price", "N/A")
            similarity = item.get("_similarity", 0)
            
            if show_similarity:
                print(f"   {i}. [Sim: {similarity:.3f}] {title} - ${price}")
            else:
                print(f"   {i}. {title} - ${price}")
    
    def run_interactive(self) -> None:
        """Interactive demo for vector search."""
        print("\n" + "=" * 60)
        print(f"  {self.name}")
        print("=" * 60)
        print(self.description)
        print("\nNew in 1.3: BFLOAT16 vector type and range queries.\n")
        
        self.setup()
        
        while True:
            print("\nOptions:")
            print("  1. KNN search (semantic query)")
            print("  2. Range query (similarity threshold)")
            print("  3. Find similar products")
            print("  4. Vector type memory comparison")
            print("  5. Custom semantic search")
            print("  q. Quit")
            
            choice = input("\nChoice: ").strip().lower()
            
            if choice == "1":
                self.demo_knn_search()
            elif choice == "2":
                threshold = input("Similarity threshold (0.5-0.9, default 0.7): ").strip()
                threshold = float(threshold) if threshold else 0.7
                self.demo_range_query(similarity_threshold=threshold)
            elif choice == "3":
                pid = input("Product ID (default 1001): ").strip() or "1001"
                self.demo_find_similar_product(pid)
            elif choice == "4":
                self.demo_vector_type_comparison()
            elif choice == "5":
                query = input("Semantic query: ").strip()
                self.demo_knn_search(query)
            elif choice == "q":
                break


if __name__ == "__main__":
    demo = VectorSearchDemo()
    demo.run_interactive()
