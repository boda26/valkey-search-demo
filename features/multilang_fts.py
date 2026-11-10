"""
Multi-Language Full-Text Search Demo

Feature: Multi-language FTS with Snowball stemmer support (12 languages)
PR: https://github.com/valkey-io/valkey-search/pull/1263

This demo shows language-aware stemming and tokenization for German, French,
Spanish, and English product searches.
"""

from core.config import config
from .base import FeatureDemo


class MultiLangFTSDemo(FeatureDemo):
    """Demo for multi-language full-text search in valkey-search 1.3."""
    
    name = "Multi-Language Full-Text Search"
    description = "Language-aware stemming/tokenization for 12 Snowball languages"
    
    def setup(self) -> None:
        """Verify multi-language indexes exist."""
        indexes = self.client.execute_command("FT._LIST")
        required = [config.index_name, config.index_name_de, config.index_name_fr]
        
        for idx in required:
            if idx not in indexes:
                print(f"Warning: Index '{idx}' not found. Run data loader first.")
    
    def demo_german_search(self, query: str = "Laufschuhe") -> list[dict]:
        """
        Search German products with German stemming.
        
        Example: "Laufschuhe" (running shoes) → stems to "Laufschuh"
        This will match "Traillaufschuhe" due to German stemming.
        """
        print(f"\n🇩🇪 German Search: '{query}'")
        print(f"   Index: {config.index_name_de} (LANGUAGE german)")
        
        results = self._execute_search(
            config.index_name_de,
            query,
            "RETURN", "3", "title", "description", "price",
        )
        
        parsed = self._parse_search_results(results)
        self._print_results(parsed, ["title", "price"])
        return parsed
    
    def demo_french_search(self, query: str = "chaussures imperméables") -> list[dict]:
        """
        Search French products with French stemming.
        
        Example: "imperméables" → stems to "imperméabl"
        """
        print(f"\n🇫🇷 French Search: '{query}'")
        print(f"   Index: {config.index_name_fr} (LANGUAGE french)")
        
        results = self._execute_search(
            config.index_name_fr,
            query,
            "RETURN", "3", "title", "description", "price",
        )
        
        parsed = self._parse_search_results(results)
        self._print_results(parsed, ["title", "price"])
        return parsed
    
    def demo_english_search(self, query: str = "running shoes waterproof") -> list[dict]:
        """
        Search English products with English stemming.
        
        Example: "running" → stems to "run", matches "Trail Running Shoes"
        """
        print(f"\n🇺🇸 English Search: '{query}'")
        print(f"   Index: {config.index_name} (LANGUAGE english)")
        
        results = self._execute_search(
            config.index_name,
            query,
            "RETURN", "3", "title", "description", "price",
        )
        
        parsed = self._parse_search_results(results)
        self._print_results(parsed, ["title", "price"])
        return parsed
    
    def demo_cross_language_comparison(self, concept: str = "headphones") -> None:
        """
        Show the same product searched in different languages.
        
        Demonstrates that each language index applies its own stemmer.
        """
        print("\n" + "=" * 60)
        print("Cross-Language Search Comparison")
        print("=" * 60)
        
        queries = [
            ("English", config.index_name, "noise cancelling headphones"),
            ("German", config.index_name_de, "Kopfhörer Geräuschunterdrückung"),
            ("French", config.index_name_fr, "casque réduction bruit"),
        ]
        
        for lang, index, query in queries:
            print(f"\n🔍 {lang}: '{query}'")
            results = self._execute_search(
                index,
                query,
                "RETURN", "2", "title", "price",
                "LIMIT", "0", "3",
            )
            parsed = self._parse_search_results(results)
            
            if parsed:
                for item in parsed:
                    print(f"   ✓ {item.get('title')} - ${item.get('price')}")
            else:
                print("   (no results)")
    
    def run_interactive(self) -> None:
        """Interactive demo for multi-language FTS."""
        print("\n" + "=" * 60)
        print(f"  {self.name}")
        print("=" * 60)
        print(self.description)
        print("\nThis demo shows language-aware stemming across languages.")
        print("Each language index uses its Snowball stemmer for proper word matching.\n")
        
        self.setup()
        
        while True:
            print("\nOptions:")
            print("  1. German search (Laufschuhe)")
            print("  2. French search (chaussures imperméables)")
            print("  3. English search (running shoes)")
            print("  4. Cross-language comparison")
            print("  5. Custom search")
            print("  q. Quit")
            
            choice = input("\nChoice: ").strip().lower()
            
            if choice == "1":
                self.demo_german_search()
            elif choice == "2":
                self.demo_french_search()
            elif choice == "3":
                self.demo_english_search()
            elif choice == "4":
                self.demo_cross_language_comparison()
            elif choice == "5":
                lang = input("Language (en/de/fr): ").strip().lower()
                query = input("Query: ").strip()
                if lang == "de":
                    self.demo_german_search(query)
                elif lang == "fr":
                    self.demo_french_search(query)
                else:
                    self.demo_english_search(query)
            elif choice == "q":
                break


if __name__ == "__main__":
    demo = MultiLangFTSDemo()
    demo.run_interactive()
