#!/usr/bin/env python3
"""
Interactive CLI Demo Runner for Valkey Search 1.3

Run individual feature demos or the combined shopping app experience.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from features import (
    MultiLangFTSDemo,
    BM25ScoringDemo,
    VectorSearchDemo,
    HybridSearchDemo,
    CursorPagingDemo,
)


console = Console()


def print_banner():
    """Print the demo banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║           Valkey Search 1.3 - Shopping App Demo               ║
║                                                               ║
║  Features:                                                    ║
║    • Multi-language FTS (12 Snowball languages)              ║
║    • BM25STD text scoring with WITHSCORES                    ║
║    • FLOAT16/BFLOAT16 vectors + Range queries                ║
║    • FT.HYBRID search with RRF/LINEAR fusion                 ║
║    • Cursor-based pagination (WITHCURSOR)                    ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_feature_table():
    """Print a table of available features."""
    table = Table(title="Available Features")
    
    table.add_column("#", style="cyan", width=3)
    table.add_column("Feature", style="green")
    table.add_column("PR", style="dim")
    
    features = [
        ("1", "Multi-language FTS", "#1263"),
        ("2", "BM25STD Scoring", "#1287"),
        ("3", "Vector Search (BFLOAT16 + Range)", "#1001, #985"),
        ("4", "FT.HYBRID Search", "#1083"),
        ("5", "Cursor Pagination", "#1394"),
        ("6", "Combined Shopping Demo", "-"),
    ]
    
    for row in features:
        table.add_row(*row)
    
    console.print(table)


def run_combined_demo():
    """Run a combined shopping app demo showcasing all features."""
    console.print("\n[bold green]Combined Shopping App Demo[/]")
    console.print("=" * 60)
    
    # Initialize all demos
    multilang = MultiLangFTSDemo()
    bm25 = BM25ScoringDemo()
    vector = VectorSearchDemo()
    hybrid = HybridSearchDemo()
    cursor = CursorPagingDemo()
    
    # Scenario 1: Multi-language search
    console.print("\n[bold]Scenario 1: Multi-language Store[/]")
    console.print("User switches store language to German and searches for running shoes")
    multilang.demo_german_search("Laufschuhe wasserdicht")
    
    input("\nPress Enter to continue...")
    
    # Scenario 2: Scored search for best match
    console.print("\n[bold]Scenario 2: Best Match Ranking[/]")
    console.print("User searches for 'wireless headphones' - show relevance scores")
    bm25.demo_search_with_scores("wireless headphones")
    
    input("\nPress Enter to continue...")
    
    # Scenario 3: Similar products
    console.print("\n[bold]Scenario 3: Similar Products[/]")
    console.print("User views a product - show similar items using vector search")
    vector.demo_find_similar_product("1001")
    
    input("\nPress Enter to continue...")
    
    # Scenario 4: Hybrid search
    console.print("\n[bold]Scenario 4: Smart Search[/]")
    console.print("User searches: 'comfortable office chair for working from home'")
    hybrid.demo_hybrid_rrf("comfortable office chair for working from home")
    
    input("\nPress Enter to continue...")
    
    # Scenario 5: Paginated results
    console.print("\n[bold]Scenario 5: Browse All Products[/]")
    console.print("User browses catalog with infinite scroll")
    cursor.demo_paginated_search("*", page_size=3, max_pages=3)


def main():
    """Main entry point for the CLI demo."""
    print_banner()
    
    while True:
        print_feature_table()
        
        console.print("\n[bold]Options:[/]")
        console.print("  Enter a number (1-6) to run a demo")
        console.print("  q - Quit")
        console.print("  s - Setup: Generate and load sample data")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice == "q":
            console.print("\n[green]Thanks for watching the demo![/]")
            break
        
        elif choice == "s":
            console.print("\n[yellow]Setting up demo data...[/]")
            from core.data_loader import DataLoader
            from pathlib import Path
            
            loader = DataLoader()
            data_dir = Path(__file__).parent.parent / "data"
            
            if not (data_dir / "products_en.json").exists():
                loader.generate_sample_data(data_dir)
            
            loader.load_all_sample_data(data_dir)
            console.print("[green]Setup complete![/]")
        
        elif choice == "1":
            demo = MultiLangFTSDemo()
            demo.run_interactive()
        
        elif choice == "2":
            demo = BM25ScoringDemo()
            demo.run_interactive()
        
        elif choice == "3":
            demo = VectorSearchDemo()
            demo.run_interactive()
        
        elif choice == "4":
            demo = HybridSearchDemo()
            demo.run_interactive()
        
        elif choice == "5":
            demo = CursorPagingDemo()
            demo.run_interactive()
        
        elif choice == "6":
            run_combined_demo()
        
        else:
            console.print("[red]Invalid choice. Please try again.[/]")


if __name__ == "__main__":
    main()
