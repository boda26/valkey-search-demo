"""
Search Cursor Pagination Demo

Feature: WITHCURSOR and FT.CURSOR for paginated results
PR: https://github.com/valkey-io/valkey-search/pull/1394

This demo shows cursor-based pagination through large result sets.
"""

from core.config import config
from .base import FeatureDemo


class CursorPagingDemo(FeatureDemo):
    """Demo for cursor-based pagination in valkey-search 1.3."""
    
    name = "Cursor-Based Pagination"
    description = "WITHCURSOR and FT.CURSOR READ/DEL for paging through large result sets"
    
    def setup(self) -> None:
        """Verify index exists."""
        indexes = self.client.execute_command("FT._LIST")
        if config.index_name not in indexes:
            print(f"Warning: Index '{config.index_name}' not found. Run data loader first.")
    
    def demo_paginated_search(
        self,
        query: str = "*",
        page_size: int = 3,
        max_pages: int = 5,
    ) -> None:
        """
        Paginated search with cursors.
        
        Instead of re-running the query for each page, cursors let you:
        1. Run the query once with WITHCURSOR
        2. Get the first page + a cursor_id
        3. Use FT.CURSOR READ to get subsequent pages
        4. Clean up with FT.CURSOR DEL when done
        """
        print(f"\n📄 Paginated Search: '{query}'")
        print(f"   Page size: {page_size}, Max pages: {max_pages}")
        print("   Using: WITHCURSOR + FT.CURSOR READ")
        
        # First page - use WITHCURSOR
        print("\n   [Initial query with WITHCURSOR]")
        results = self._execute_search(
            config.index_name,
            query,
            "WITHCURSOR",
            "COUNT", str(page_size),
            "RETURN", "3", "title", "price", "category",
        )
        
        cursor_id, page_results = self._parse_cursor_results(results)
        page_num = 1
        
        print(f"\n   Page {page_num}: {len(page_results)} results")
        self._print_page(page_results)
        
        # Subsequent pages - use FT.CURSOR READ
        while cursor_id and page_num < max_pages:
            input(f"\n   Press Enter for page {page_num + 1}...")
            
            results = self.client.execute_command(
                "FT.CURSOR", "READ",
                config.index_name,
                cursor_id,
                "COUNT", str(page_size),
            )
            
            cursor_id, page_results = self._parse_cursor_results(results)
            page_num += 1
            
            if page_results:
                print(f"\n   Page {page_num}: {len(page_results)} results")
                self._print_page(page_results)
            else:
                print(f"\n   Page {page_num}: No more results")
                break
        
        # Clean up cursor
        if cursor_id:
            self.client.execute_command("FT.CURSOR", "DEL", config.index_name, cursor_id)
            print("\n   [Cursor deleted]")
        else:
            print("\n   [End of results - cursor auto-deleted]")
    
    def demo_cursor_lifecycle(self) -> None:
        """
        Demonstrate cursor lifecycle management.
        
        Cursors:
        - Are created with WITHCURSOR
        - Have a configurable timeout
        - Should be deleted when no longer needed
        - Auto-delete when exhausted
        """
        print("\n🔄 Cursor Lifecycle Demo")
        print("=" * 60)
        
        print("\n   1. Create cursor with WITHCURSOR:")
        print("      FT.SEARCH idx '*' WITHCURSOR COUNT 5")
        
        results = self._execute_search(
            config.index_name,
            "*",
            "WITHCURSOR",
            "COUNT", "2",
            "RETURN", "1", "title",
        )
        
        cursor_id, page_results = self._parse_cursor_results(results)
        print(f"      → Cursor ID: {cursor_id}")
        print(f"      → First page: {len(page_results)} results")
        
        print("\n   2. Read next page with FT.CURSOR READ:")
        print(f"      FT.CURSOR READ idx {cursor_id} COUNT 2")
        
        results = self.client.execute_command(
            "FT.CURSOR", "READ",
            config.index_name,
            cursor_id,
            "COUNT", "2",
        )
        
        cursor_id, page_results = self._parse_cursor_results(results)
        print(f"      → Cursor ID: {cursor_id}")
        print(f"      → Second page: {len(page_results)} results")
        
        print("\n   3. Delete cursor with FT.CURSOR DEL:")
        print(f"      FT.CURSOR DEL idx {cursor_id}")
        
        if cursor_id:
            self.client.execute_command("FT.CURSOR", "DEL", config.index_name, cursor_id)
            print("      → Cursor deleted successfully")
        
        print("\n   💡 Best practices:")
        print("      • Always delete cursors when done")
        print("      • Set appropriate timeout for long sessions")
        print("      • Cursors auto-delete when results exhausted")
    
    def demo_infinite_scroll(self, query: str = "*") -> None:
        """
        Simulate infinite scroll UI pattern.
        
        User scrolls → Load more → User scrolls → Load more...
        """
        print("\n♾️ Infinite Scroll Simulation")
        print("   (Press Enter to 'scroll' and load more, 'q' to stop)")
        print("=" * 60)
        
        page_size = 3
        total_loaded = 0
        
        # Initial load
        results = self._execute_search(
            config.index_name,
            query,
            "WITHCURSOR",
            "COUNT", str(page_size),
            "RETURN", "2", "title", "price",
        )
        
        cursor_id, page_results = self._parse_cursor_results(results)
        total_loaded += len(page_results)
        
        print(f"\n   Initial load: {len(page_results)} items")
        self._print_page(page_results)
        
        while cursor_id:
            user_input = input(f"\n   [Loaded {total_loaded} items] Scroll for more (Enter/q): ")
            
            if user_input.lower() == "q":
                # Clean up
                self.client.execute_command("FT.CURSOR", "DEL", config.index_name, cursor_id)
                print("   [Session ended, cursor deleted]")
                break
            
            results = self.client.execute_command(
                "FT.CURSOR", "READ",
                config.index_name,
                cursor_id,
                "COUNT", str(page_size),
            )
            
            cursor_id, page_results = self._parse_cursor_results(results)
            
            if page_results:
                total_loaded += len(page_results)
                print(f"\n   Loaded {len(page_results)} more items:")
                self._print_page(page_results)
            else:
                print("\n   [End of results]")
                break
        
        print(f"\n   Total items loaded: {total_loaded}")
    
    def _parse_cursor_results(self, results: list) -> tuple[int | None, list[dict]]:
        """
        Parse cursor search results.
        
        Format: [[total, key1, [fields], ...], cursor_id]
        When cursor_id is 0, there are no more results.
        """
        if not results or len(results) < 2:
            return None, []
        
        # Results are wrapped: [[search_results], cursor_id]
        search_results = results[0]
        cursor_id = results[1]
        
        # Cursor ID of 0 means no more results
        if cursor_id == 0:
            cursor_id = None
        
        # Parse the search results
        items = []
        if search_results and search_results[0] > 0:
            i = 1
            while i < len(search_results):
                key = search_results[i]
                fields = search_results[i + 1] if i + 1 < len(search_results) else []
                
                item = {"_key": key}
                for j in range(0, len(fields), 2):
                    item[fields[j]] = fields[j + 1]
                
                items.append(item)
                i += 2
        
        return cursor_id, items
    
    def _print_page(self, results: list[dict]) -> None:
        """Print a page of results."""
        for item in results:
            title = item.get("title", "Unknown")
            price = item.get("price", "")
            price_str = f" - ${price}" if price else ""
            print(f"      • {title}{price_str}")
    
    def run_interactive(self) -> None:
        """Interactive demo for cursor pagination."""
        print("\n" + "=" * 60)
        print(f"  {self.name}")
        print("=" * 60)
        print(self.description)
        print("\nCursors enable efficient pagination without re-running queries.\n")
        
        self.setup()
        
        while True:
            print("\nOptions:")
            print("  1. Paginated search demo")
            print("  2. Cursor lifecycle demo")
            print("  3. Infinite scroll simulation")
            print("  4. Custom paginated search")
            print("  q. Quit")
            
            choice = input("\nChoice: ").strip().lower()
            
            if choice == "1":
                self.demo_paginated_search()
            elif choice == "2":
                self.demo_cursor_lifecycle()
            elif choice == "3":
                self.demo_infinite_scroll()
            elif choice == "4":
                query = input("Query (default '*'): ").strip() or "*"
                page_size = int(input("Page size (default 3): ").strip() or "3")
                self.demo_paginated_search(query, page_size)
            elif choice == "q":
                break


if __name__ == "__main__":
    demo = CursorPagingDemo()
    demo.run_interactive()
