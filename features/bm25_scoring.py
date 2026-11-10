"""
BM25STD Text Scoring Demo

Feature: BM25STD relevance-ranked full-text search with WITHSCORES
PR: https://github.com/valkey-io/valkey-search/pull/1287

This demo shows relevance-ranked search results with configurable scorers
and query weights.
"""

from core.config import config
from .base import FeatureDemo


class BM25ScoringDemo(FeatureDemo):
    """Demo for BM25STD text scoring in valkey-search 1.3."""
    
    name = "BM25STD Text Scoring"
    description = "Relevance-ranked full-text search with WITHSCORES and configurable scorers"
    
    def setup(self) -> None:
        """Verify index exists."""
        indexes = self.client.execute_command("FT._LIST")
        if config.index_name not in indexes:
            print(f"Warning: Index '{config.index_name}' not found. Run data loader first.")
    
    def demo_search_with_scores(self, query: str = "waterproof shoes") -> list[dict]:
        """
        Search with BM25STD scoring and return relevance scores.
        
        The WITHSCORES option returns a relevance score for each result,
        allowing the application to show users how well each result matches.
        """
        print(f"\n🎯 BM25STD Scored Search: '{query}'")
        print("   Using: SCORER BM25STD WITHSCORES")
        
        results = self._execute_search(
            config.index_name,
            query,
            "WITHSCORES",
            "SCORER", "BM25STD",
            "RETURN", "3", "title", "description", "price",
        )
        
        parsed = self._parse_search_results_with_scores(results)
        self._print_scored_results(parsed)
        return parsed
    
    def demo_weighted_fields(self, query: str = "wireless bluetooth") -> list[dict]:
        """
        Show how field weights affect scoring.
        
        The index was created with:
        - title TEXT WEIGHT 2.0
        - description TEXT (default weight 1.0)
        
        So title matches score higher than description matches.
        """
        print(f"\n⚖️ Weighted Field Search: '{query}'")
        print("   title has WEIGHT 2.0, description has WEIGHT 1.0")
        print("   Title matches will rank higher")
        
        results = self._execute_search(
            config.index_name,
            query,
            "WITHSCORES",
            "SCORER", "BM25STD",
            "RETURN", "4", "title", "description", "price", "__score",
        )
        
        parsed = self._parse_search_results_with_scores(results)
        self._print_scored_results(parsed)
        return parsed
    
    def demo_compare_scorers(self, query: str = "comfortable chair") -> None:
        """
        Compare results with different scorers.
        
        Shows how BM25STD differs from the default scorer.
        """
        print(f"\n📊 Scorer Comparison: '{query}'")
        
        # Default scorer
        print("\n  Default Scorer:")
        results_default = self._execute_search(
            config.index_name,
            query,
            "WITHSCORES",
            "RETURN", "2", "title", "price",
            "LIMIT", "0", "3",
        )
        self._print_scored_results(self._parse_search_results_with_scores(results_default))
        
        # BM25STD scorer
        print("\n  BM25STD Scorer:")
        results_bm25 = self._execute_search(
            config.index_name,
            query,
            "WITHSCORES",
            "SCORER", "BM25STD",
            "RETURN", "2", "title", "price",
            "LIMIT", "0", "3",
        )
        self._print_scored_results(self._parse_search_results_with_scores(results_bm25))
    
    def demo_field_specific_search(self, query: str = "@title:wireless @description:battery") -> list[dict]:
        """
        Search specific fields with scoring.
        
        You can target specific fields in the query to control what matches.
        """
        print(f"\n🔬 Field-Specific Search: '{query}'")
        print("   Searching title for 'wireless', description for 'battery'")
        
        results = self._execute_search(
            config.index_name,
            query,
            "WITHSCORES",
            "SCORER", "BM25STD",
            "RETURN", "3", "title", "description", "price",
        )
        
        parsed = self._parse_search_results_with_scores(results)
        self._print_scored_results(parsed)
        return parsed
    
    def _parse_search_results_with_scores(self, results: list) -> list[dict]:
        """
        Parse FT.SEARCH results that include scores.
        
        With WITHSCORES, format is: [total, key1, score1, [fields1], key2, score2, ...]
        """
        if not results or results[0] == 0:
            return []
        
        items = []
        i = 1
        while i < len(results):
            key = results[i]
            score = results[i + 1] if i + 1 < len(results) else 0
            fields = results[i + 2] if i + 2 < len(results) else []
            
            item = {"_key": key, "_score": float(score)}
            for j in range(0, len(fields), 2):
                item[fields[j]] = fields[j + 1]
            
            items.append(item)
            i += 3
        
        return items
    
    def _print_scored_results(self, results: list[dict]) -> None:
        """Print results with their scores."""
        if not results:
            print("   No results found.")
            return
        
        print(f"\n   Found {len(results)} result(s):\n")
        
        for i, item in enumerate(results, 1):
            score = item.get("_score", 0)
            title = item.get("title", "Unknown")
            price = item.get("price", "N/A")
            
            # Visual score bar
            bar_len = int(score * 20) if score <= 1 else int(min(score, 10) * 2)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            
            print(f"   {i}. [{bar}] {score:.4f}")
            print(f"      {title}")
            if price != "N/A":
                print(f"      ${price}")
            print()
    
    def run_interactive(self) -> None:
        """Interactive demo for BM25 scoring."""
        print("\n" + "=" * 60)
        print(f"  {self.name}")
        print("=" * 60)
        print(self.description)
        print("\nBM25STD provides industry-standard relevance ranking.")
        print("Results are scored based on term frequency and document length.\n")
        
        self.setup()
        
        while True:
            print("\nOptions:")
            print("  1. Search with scores (waterproof shoes)")
            print("  2. Weighted field demo (wireless bluetooth)")
            print("  3. Compare scorers (comfortable chair)")
            print("  4. Field-specific search")
            print("  5. Custom scored search")
            print("  q. Quit")
            
            choice = input("\nChoice: ").strip().lower()
            
            if choice == "1":
                self.demo_search_with_scores()
            elif choice == "2":
                self.demo_weighted_fields()
            elif choice == "3":
                self.demo_compare_scorers()
            elif choice == "4":
                self.demo_field_specific_search()
            elif choice == "5":
                query = input("Query: ").strip()
                self.demo_search_with_scores(query)
            elif choice == "q":
                break


if __name__ == "__main__":
    demo = BM25ScoringDemo()
    demo.run_interactive()
