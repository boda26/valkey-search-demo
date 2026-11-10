"""
FT.HYBRID Search Demo

Feature: Native text + vector hybrid search with score fusion
PR: https://github.com/valkey-io/valkey-search/pull/1083

This demo shows combined keyword and semantic search with RRF and LINEAR fusion.
"""

from core.config import config
from core.data_loader import DataLoader
from .base import FeatureDemo


class HybridSearchDemo(FeatureDemo):
    """Demo for FT.HYBRID in valkey-search 1.3."""
    
    name = "FT.HYBRID Search"
    description = "Native text + vector hybrid search with RRF, LINEAR, and custom fusion"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._embedder = None
    
    @property
    def embedder(self):
        """Lazy-load the embedding model."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(config.embedding_model)
        return self._embedder
    
    def setup(self) -> None:
        """Verify index exists."""
        indexes = self.client.execute_command("FT._LIST")
        if config.index_name not in indexes:
            print(f"Warning: Index '{config.index_name}' not found. Run data loader first.")
    
    def demo_hybrid_rrf(
        self,
        query: str = "comfortable shoes for standing all day",
        category: str | None = None,
    ) -> list[dict]:
        """
        Hybrid search with RRF (Reciprocal Rank Fusion).
        
        RRF combines text and vector rankings:
        - Each result gets a score based on its rank in both lists
        - RRF = 1/(k + rank_text) + 1/(k + rank_vector)
        - Best of both worlds: keyword precision + semantic understanding
        """
        print(f"\n🔀 Hybrid Search (RRF): '{query}'")
        if category:
            print(f"   Filter: category = {category}")
        
        # Generate query embedding
        query_vec = self._encode_query(query)
        
        # Build filter clause
        filter_clause = f"@category:{{{category}}}" if category else "*"
        
        results = self.client.execute_command(
            "FT.HYBRID",
            config.index_name,
            # Text query
            "TEXT", query,
            # Vector query
            "VECTOR", "KNN", "5", "@embedding", "query_vec",
            # Fusion method
            "FUSION", "RRF",
            # Filter
            "FILTER", filter_clause,
            # Parameters
            "PARAMS", "2", "query_vec", query_vec,
            # Return fields
            "RETURN", "4", "title", "price", "category", "description",
            "LIMIT", "0", "5",
        )
        
        parsed = self._parse_hybrid_results(results)
        self._print_hybrid_results(parsed, "RRF")
        return parsed
    
    def demo_hybrid_linear(
        self,
        query: str = "wireless bluetooth headphones",
        text_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> list[dict]:
        """
        Hybrid search with LINEAR score fusion.
        
        LINEAR combines scores with explicit weights:
        - final_score = text_weight * text_score + vector_weight * vector_score
        - Gives you fine-grained control over the balance
        """
        print(f"\n⚖️ Hybrid Search (LINEAR): '{query}'")
        print(f"   Weights: text={text_weight}, vector={vector_weight}")
        
        query_vec = self._encode_query(query)
        
        results = self.client.execute_command(
            "FT.HYBRID",
            config.index_name,
            "TEXT", query,
            "VECTOR", "KNN", "5", "@embedding", "query_vec",
            "FUSION", "LINEAR", str(text_weight), str(vector_weight),
            "PARAMS", "2", "query_vec", query_vec,
            "RETURN", "3", "title", "price", "category",
            "LIMIT", "0", "5",
        )
        
        parsed = self._parse_hybrid_results(results)
        self._print_hybrid_results(parsed, "LINEAR")
        return parsed
    
    def demo_compare_text_vs_vector_vs_hybrid(
        self,
        query: str = "noise cancelling for focus work",
    ) -> None:
        """
        Compare text-only, vector-only, and hybrid search results.
        
        Shows how hybrid search combines the strengths of both approaches.
        """
        print(f"\n📊 Comparison: '{query}'")
        print("=" * 60)
        
        query_vec = self._encode_query(query)
        
        # Text-only search
        print("\n1️⃣ TEXT ONLY (keyword matching):")
        text_results = self._execute_search(
            config.index_name,
            query,
            "RETURN", "2", "title", "price",
            "LIMIT", "0", "3",
        )
        for item in self._parse_search_results(text_results):
            print(f"   • {item.get('title')}")
        if not text_results or text_results[0] == 0:
            print("   (no results)")
        
        # Vector-only search
        print("\n2️⃣ VECTOR ONLY (semantic similarity):")
        vector_results = self._execute_search(
            config.index_name,
            "(*)=>[KNN 3 @embedding $query_vec]",
            "PARAMS", "2", "query_vec", query_vec,
            "RETURN", "2", "title", "price",
            "DIALECT", "2",
        )
        for item in self._parse_search_results(vector_results):
            print(f"   • {item.get('title')}")
        
        # Hybrid search
        print("\n3️⃣ HYBRID (RRF fusion):")
        hybrid_results = self.client.execute_command(
            "FT.HYBRID",
            config.index_name,
            "TEXT", query,
            "VECTOR", "KNN", "3", "@embedding", "query_vec",
            "FUSION", "RRF",
            "PARAMS", "2", "query_vec", query_vec,
            "RETURN", "2", "title", "price",
            "LIMIT", "0", "3",
        )
        for item in self._parse_hybrid_results(hybrid_results):
            print(f"   • {item.get('title')}")
        
        print("\n💡 Hybrid combines exact keyword matches with semantic understanding")
    
    def demo_shopping_use_case(self) -> None:
        """
        Real-world e-commerce search scenario.
        
        User searches: "red running shoes for marathon"
        - Text matches: "running", "shoes", "marathon"
        - Vector matches: semantic similarity to athletic footwear
        - Combined: best results for the user's intent
        """
        print("\n🛒 E-Commerce Search Demo")
        print("=" * 60)
        
        queries = [
            ("budget friendly headphones", "electronics"),
            ("waterproof outdoor gear", None),
            ("ergonomic work from home setup", None),
        ]
        
        for query, category in queries:
            print(f"\n🔍 Search: '{query}'")
            if category:
                print(f"   Category filter: {category}")
            
            self.demo_hybrid_rrf(query, category)
    
    def _encode_query(self, query: str) -> bytes:
        """Encode a query string to BFLOAT16 vector bytes."""
        embedding = self.embedder.encode(query)
        return DataLoader._vector_to_bytes(embedding, dtype="bfloat16")
    
    def _parse_hybrid_results(self, results: list) -> list[dict]:
        """Parse FT.HYBRID results."""
        if not results or (isinstance(results[0], int) and results[0] == 0):
            return []
        
        # FT.HYBRID returns: [total, key1, [fields], key2, [fields], ...]
        items = []
        
        # Handle different result formats
        if isinstance(results[0], int):
            # Format: [total, key1, [fields], ...]
            i = 1
            while i < len(results):
                key = results[i]
                fields = results[i + 1] if i + 1 < len(results) else []
                
                item = {"_key": key}
                for j in range(0, len(fields), 2):
                    item[fields[j]] = fields[j + 1]
                
                items.append(item)
                i += 2
        
        return items
    
    def _print_hybrid_results(self, results: list[dict], fusion_type: str) -> None:
        """Print hybrid search results."""
        if not results:
            print("   No results found.")
            return
        
        print(f"\n   {fusion_type} Fusion Results ({len(results)} items):\n")
        
        for i, item in enumerate(results, 1):
            title = item.get("title", "Unknown")
            price = item.get("price", "N/A")
            category = item.get("category", "")
            
            print(f"   {i}. {title}")
            print(f"      ${price} | {category}")
    
    def run_interactive(self) -> None:
        """Interactive demo for hybrid search."""
        print("\n" + "=" * 60)
        print(f"  {self.name}")
        print("=" * 60)
        print(self.description)
        print("\nFT.HYBRID combines text relevance with semantic similarity.\n")
        
        self.setup()
        
        while True:
            print("\nOptions:")
            print("  1. Hybrid search with RRF fusion")
            print("  2. Hybrid search with LINEAR fusion")
            print("  3. Compare text vs vector vs hybrid")
            print("  4. E-commerce search scenarios")
            print("  5. Custom hybrid search")
            print("  q. Quit")
            
            choice = input("\nChoice: ").strip().lower()
            
            if choice == "1":
                self.demo_hybrid_rrf()
            elif choice == "2":
                self.demo_hybrid_linear()
            elif choice == "3":
                self.demo_compare_text_vs_vector_vs_hybrid()
            elif choice == "4":
                self.demo_shopping_use_case()
            elif choice == "5":
                query = input("Query: ").strip()
                self.demo_hybrid_rrf(query)
            elif choice == "q":
                break


if __name__ == "__main__":
    demo = HybridSearchDemo()
    demo.run_interactive()
